from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from eth_abi.abi import encode
from web3 import Web3
from colorama import *
from datetime import datetime
import asyncio, random, secrets, time, os, json


# Load configuration
try:
    with open('config.json', 'r') as file:
        config = json.load(file)
except (FileNotFoundError, json.JSONDecodeError) as e:
    raise Exception(f"Config file error: {e}")

local_tz = datetime.now().astimezone().tzinfo


def get_phantom_headers():
    return {
        "accept": "*/*",
        # "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "chrome-extension://bfnaelmomeimhlpmgjnjophhpkkoljpa",
        "priority": "u=1, i",
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Microsoft Edge";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "none",
        "sec-fetch-storage-access": "active",
        "user-agent": FakeUserAgent().random,
        "x-phantom-platform": "extension",
        "x-phantom-version": "25.9.1"
    }


async def timeout_with_log(start=60, end=300):
    """Custom timeout function with logging"""
    time_out = random.randint(start, end)

    hours = time_out // 3600
    minutes = (time_out % 3600) // 60
    seconds = time_out % 60

    if hours > 0:
        time_str = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        time_str = f"{minutes}m {seconds}s"
    else:
        time_str = f"{seconds}s"

    timestamp = datetime.now().astimezone(local_tz).strftime('%x %X')
    print(
        f"{Fore.CYAN + Style.BRIGHT}[ {timestamp} ]{Style.RESET_ALL}{Fore.BLUE + Style.BRIGHT} ⏳ Waiting {time_str}{Style.RESET_ALL}")
    await asyncio.sleep(time_out)


def log(message):
    timestamp = datetime.now().astimezone(local_tz).strftime('%x %X')
    print(
        f"{Fore.CYAN + Style.BRIGHT}[ {timestamp} ]{Style.RESET_ALL}{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
        flush=True)


def get_random_amount(config_key):
    amount_range = config.get(config_key, [0.001, 0.005])
    if not isinstance(amount_range, list) or len(amount_range) != 2:
        amount_range = [0.001, 0.005]
    return round(random.uniform(amount_range[0], amount_range[1]), 6)


def get_short_timeout():
    """Get random short timeout from config"""
    timeout_range = config.get("shortTimeout", [5, 20])
    if not isinstance(timeout_range, list) or len(timeout_range) != 2:
        timeout_range = [5, 20]
    return timeout_range[0], timeout_range[1]


class PharosBot:
    def __init__(self):
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://testnet.pharosnetwork.xyz",
            "Referer": "https://testnet.pharosnetwork.xyz/",
            "User-Agent": FakeUserAgent().random
        }
        self.BASE_API = "https://api.pharosnetwork.xyz"
        self.RPC_URL = "https://testnet.dplabs-internal.com"
        self.CONTRACTS = {
            'PHRS': "0xf6a07fe10e28a70d1b0f36c7eb7745d2bae2a312",
            'WPHRS': "0x76aaada469d23216be5f7c596fa25f282ff9b364",
            'USDC': "0xad902cf99c2de2f1ba5ec4d642fd7e49cae9ee37",
            'ROUTER': "0x1a4de519154ae51200b0ad7c90f7fac75547888a"
        }
        self.ERC20_ABI = [
            {"inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf",
             "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
            {"inputs": [{"name": "spender", "type": "address"}, {"name": "value", "type": "uint256"}],
             "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
            {"inputs": [], "name": "deposit", "outputs": [], "stateMutability": "payable", "type": "function"},
            {"inputs": [{"name": "wad", "type": "uint256"}], "name": "withdraw", "outputs": [], "type": "function"}
        ]
        self.MULTICALL_ABI = [
            {"inputs": [{"internalType": "uint256", "name": "collectionAndSelfcalls", "type": "uint256"},
                        {"internalType": "bytes[]", "name": "data", "type": "bytes[]"}], "name": "multicall",
             "outputs": [], "type": "function"}
        ]
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.failed_proxies = set()  # Track failed proxies
        self.proxy_attempts = {}  # Track attempts per proxy per address

    async def load_proxies(self):
        if not config.get('useProxy', False):
            return

        filename = "proxy.txt"
        try:
            if config.get('proxyType') == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get(
                            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt") as response:
                        response.raise_for_status()
                        content = await response.text()
                        with open(filename, 'w') as f:
                            f.write(content)
                        self.proxies = content.splitlines()
            else:
                if os.path.exists(filename):
                    with open(filename, 'r') as f:
                        self.proxies = f.read().splitlines()

            if self.proxies:
                log(f"{Fore.GREEN}Loaded {len(self.proxies)} proxies{Style.RESET_ALL}")
        except Exception as e:
            log(f"{Fore.RED}Failed to load proxies: {e}{Style.RESET_ALL}")

    def is_proxy_error(self, error_msg):
        """Check if the error is proxy-related"""
        proxy_error_keywords = [
            "couldn't connect to proxy",
            "proxy connection failed",
            "connection timeout",
            "semaphore timeout",
            "connection refused",
            "timed out",
            "unreachable",
            "connection reset",
            "proxy error"
        ]
        error_lower = str(error_msg).lower()
        return any(keyword in error_lower for keyword in proxy_error_keywords)

    def get_next_proxy_for_address(self, address):
        """Get the next available proxy for an address, skipping failed ones"""
        if not self.proxies:
            return None

        max_attempts = len(self.proxies)
        attempts = 0

        while attempts < max_attempts:
            proxy = self.proxies[self.proxy_index]
            if not any(proxy.startswith(scheme) for scheme in ["http://", "https://", "socks4://", "socks5://"]):
                proxy = f"http://{proxy}"

            # Skip globally failed proxies temporarily
            if proxy not in self.failed_proxies:
                self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
                return proxy

            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
            attempts += 1

        # If all proxies are marked as failed, clear the failed set and try again
        if self.failed_proxies:
            log(f"{Fore.YELLOW}All proxies marked as failed, clearing failed proxy list{Style.RESET_ALL}")
            self.failed_proxies.clear()
            proxy = self.proxies[self.proxy_index]
            if not any(proxy.startswith(scheme) for scheme in ["http://", "https://", "socks4://", "socks5://"]):
                proxy = f"http://{proxy}"
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
            return proxy

        return None

    def rotate_proxy_for_address(self, address, failed_proxy):
        """Rotate to a new proxy for a specific address when current one fails"""
        if not config.get('useProxy', False) or not self.proxies:
            return None

        # Mark the failed proxy
        if failed_proxy:
            self.failed_proxies.add(failed_proxy)
            log(
                f"{Fore.YELLOW}Marked proxy as failed: {failed_proxy.replace('http://', '').replace('https://', '')}{Style.RESET_ALL}")

        # Get new proxy for this address
        new_proxy = self.get_next_proxy_for_address(address)
        if new_proxy:
            self.account_proxies[address] = new_proxy
            proxy_display = new_proxy.replace('http://', '').replace('https://', '')
            log(f"{Fore.CYAN}Rotated to new proxy for {address[:6]}...{address[-4:]}: {proxy_display}{Style.RESET_ALL}")

        return new_proxy

    def get_proxy(self, address):
        if not config.get('useProxy', False) or not self.proxies:
            return None

        if address not in self.account_proxies:
            proxy = self.get_next_proxy_for_address(address)
            if proxy:
                self.account_proxies[address] = proxy

        return self.account_proxies.get(address)

    def get_web3(self, address):
        request_kwargs = {"headers": get_phantom_headers()}
        proxy = self.get_proxy(address)
        if proxy:
            request_kwargs["proxies"] = {'https': proxy, 'http': proxy}

        provider = Web3.HTTPProvider(self.RPC_URL, request_kwargs=request_kwargs)
        w3 = Web3(provider)
        if not w3.is_connected():
            raise Exception("Failed to connect to network")
        return w3

    def generate_address(self, private_key):
        return Account.from_key(private_key).address

    def generate_random_receiver(self):
        private_key_bytes = secrets.token_bytes(32)
        return Account.from_key(to_hex(private_key_bytes)).address

    def create_login_url(self, private_key, address):
        encoded_message = encode_defunct(text="pharos")
        signed_message = Account.sign_message(encoded_message, private_key=private_key)
        signature = to_hex(signed_message.signature)
        return f"{self.BASE_API}/user/login?address={address}&signature={signature}&invite_code={config['referralCode']}"

    def get_balance(self, address, token='PHRS'):
        w3 = self.get_web3(address)
        if token == 'PHRS':
            balance = w3.eth.get_balance(address)
            decimals = 18
        else:
            contract = w3.eth.contract(address=Web3.to_checksum_address(self.CONTRACTS[token]), abi=self.ERC20_ABI)
            balance = contract.functions.balanceOf(address).call()
            decimals = contract.functions.decimals().call()
        return balance / (10 ** decimals)

    async def api_call(self, method, url, address, token=None, retries=3):
        proxy = self.get_proxy(address)
        headers = {**self.headers}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if method == "POST":
            headers["Content-Length"] = "0"

        for attempt in range(retries):
            try:
                connector = ProxyConnector.from_url(proxy) if proxy else None
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with getattr(session, method.lower())(url, headers=headers) as response:
                        response.raise_for_status()
                        return await response.json()
            except Exception as e:
                # Check if this is a proxy error and we should rotate
                if proxy and self.is_proxy_error(str(e)):
                    log(f"{Fore.YELLOW}Proxy error detected: {str(e)[:100]}...{Style.RESET_ALL}")
                    new_proxy = self.rotate_proxy_for_address(address, proxy)
                    if new_proxy:
                        proxy = new_proxy
                        # Don't count proxy rotation as a retry attempt
                        continue

                if attempt < retries - 1:
                    await asyncio.sleep(5)
                    continue
                raise e

    async def login(self, address, login_url):
        return await self.api_call("POST", login_url, address)

    async def get_profile(self, address, token):
        url = f"{self.BASE_API}/user/profile?address={address}"
        return await self.api_call("GET", url, address, token)

    async def checkin(self, address, token):
        url = f"{self.BASE_API}/sign/in?address={address}"
        return await self.api_call("POST", url, address, token)

    async def claim_faucet(self, address, token):
        status_url = f"{self.BASE_API}/faucet/status?address={address}"
        faucet_url = f"{self.BASE_API}/faucet/daily?address={address}"

        status = await self.api_call("GET", status_url, address, token)
        if status and status.get("data", {}).get("is_able_to_faucet", False):
            faucet_response = await self.api_call("POST", faucet_url, address, token)
            msg = faucet_response.get('msg', '')
            if msg == 'ok':
                return faucet_response
            else:
                raise Exception(f"{msg}")
        return status

    async def verify_transfer(self, address, token, tx_hash):
        url = f"{self.BASE_API}/task/verify?address={address}&task_id=103&tx_hash={tx_hash}"
        verify_response = await self.api_call("POST", url, address, token)
        if verify_response and verify_response.get("msg") == "task verified successfully":
            return verify_response
        else:
            raise Exception(f"{verify_response.get('msg', 'Transfer verification failed')}")

    def transfer(self, private_key, address, receiver, amount):
        w3 = self.get_web3(address)
        txn = {
            "to": receiver,
            "value": w3.to_wei(amount, "ether"),
            "nonce": w3.eth.get_transaction_count(address),
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
            "chainId": w3.eth.chain_id
        }
        signed_tx = w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = w3.to_hex(w3.eth.send_raw_transaction(signed_tx.raw_transaction))
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        # display
        log(f"{Fore.GREEN}Sent {amount} PHRS to {receiver}{Style.RESET_ALL}")
        return tx_hash, receipt.blockNumber

    def wrap_unwrap(self, private_key, address, amount, is_wrap=True):
        w3 = self.get_web3(address)
        contract = w3.eth.contract(address=Web3.to_checksum_address(self.CONTRACTS['WPHRS']), abi=self.ERC20_ABI)

        if is_wrap:
            txn = contract.functions.deposit().build_transaction({
                "from": address, "value": w3.to_wei(amount, "ether"), "gas": 50000,
                "gasPrice": w3.eth.gas_price, "nonce": w3.eth.get_transaction_count(address)
            })
        else:
            txn = contract.functions.withdraw(w3.to_wei(amount, "ether")).build_transaction({
                "from": address, "gas": 50000, "gasPrice": w3.eth.gas_price,
                "nonce": w3.eth.get_transaction_count(address)
            })

        signed_tx = w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = w3.to_hex(w3.eth.send_raw_transaction(signed_tx.raw_transaction))
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash, receipt.blockNumber

    def swap_tokens(self, private_key, address, from_token, to_token, amount):
        w3 = self.get_web3(address)

        # Approve
        token_contract = w3.eth.contract(address=Web3.to_checksum_address(self.CONTRACTS[from_token]),
                                         abi=self.ERC20_ABI)
        approve_tx = token_contract.functions.approve(Web3.to_checksum_address(self.CONTRACTS['ROUTER']),
                                                      2 ** 256 - 1).build_transaction({
            "from": address, "gas": 50000, "gasPrice": w3.eth.gas_price, "nonce": w3.eth.get_transaction_count(address)
        })
        signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key)
        w3.eth.send_raw_transaction(signed_approve.raw_transaction)
        w3.eth.wait_for_transaction_receipt(signed_approve.hash)

        # Swap
        data = encode(['address', 'address', 'uint256', 'address', 'uint256', 'uint256', 'uint256'],
                      [Web3.to_checksum_address(self.CONTRACTS[from_token]),
                       Web3.to_checksum_address(self.CONTRACTS[to_token]),
                       500, Web3.to_checksum_address(address), w3.to_wei(amount, "ether"), 0, 0])
        multicall_data = [b'\x04\xe4\x5a\xaf' + data]

        router_contract = w3.eth.contract(address=Web3.to_checksum_address(self.CONTRACTS['ROUTER']),
                                          abi=self.MULTICALL_ABI)

        # Build transaction for gas estimation (without gasPrice and nonce)
        swap_tx_for_estimate = {
            "from": address
        }

        # Estimate gas separately
        estimated_gas = router_contract.functions.multicall(int(time.time()), multicall_data).estimate_gas(
            swap_tx_for_estimate)

        # Now build the complete transaction
        swap_tx = router_contract.functions.multicall(int(time.time()), multicall_data).build_transaction({
            "from": address,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(address),
            "gas": estimated_gas
        })

        signed_swap = w3.eth.account.sign_transaction(swap_tx, private_key)
        tx_hash = w3.to_hex(w3.eth.send_raw_transaction(signed_swap.raw_transaction))
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return tx_hash, receipt.blockNumber


async def retry_operation(operation, *args, max_retries=3, operation_name="Operation"):
    """
    Enhanced retry logic with proxy rotation support:
    1. Attempts the operation up to max_retries times
    2. If operation is async (coroutine function), awaits it
    3. If operation is sync, calls it directly
    4. On failure, logs the error and waits before retry
    5. Returns result on success, None on final failure
    """
    for attempt in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(operation):
                result = await operation(*args)
            else:
                result = operation(*args)
            return result
        except Exception as e:
            log(f"{Fore.RED}{operation_name} failed (attempt {attempt + 1}/{max_retries}): {e}{Style.RESET_ALL}")
            if attempt < max_retries - 1:
                await timeout_with_log(30, 60)
    return None


async def process_account(bot, private_key, address):
    separator = "=" * 25
    masked_address = address[:6] + '*' * 6 + address[-6:]
    log(f"{Fore.CYAN}{separator}[ {masked_address} ]{separator}{Style.RESET_ALL}")

    # Show current proxy for this address
    current_proxy = bot.get_proxy(address)
    if current_proxy:
        proxy_display = current_proxy.replace('http://', '').replace('https://', '')
        log(f"{Fore.MAGENTA}Using proxy: {proxy_display}{Style.RESET_ALL}")

    # Login
    login_url = bot.create_login_url(private_key, address)
    login_result = await retry_operation(bot.login, address, login_url, operation_name="Login")
    if not login_result or "data" not in login_result:
        log(f"{Fore.RED}Login failed, skipping account{Style.RESET_ALL}")
        return

    token = login_result["data"]["jwt"]
    log(f"{Fore.GREEN}Login successful{Style.RESET_ALL}")

    # Get profile and check in
    profile = await retry_operation(bot.get_profile, address, token, operation_name="Profile")
    points = profile.get("data", {}).get("user_info", {}).get("TotalPoints", "N/A") if profile else "N/A"
    log(f"{Fore.WHITE}Points: {points}{Style.RESET_ALL}")

    checkin_result = await retry_operation(bot.checkin, address, token, operation_name="Check-in")
    if checkin_result:
        msg = checkin_result.get("msg", "")
        if msg == "ok":
            log(f"{Fore.GREEN}Check-in claimed{Style.RESET_ALL}")
        elif "already" in msg:
            log(f"{Fore.YELLOW}Already checked in{Style.RESET_ALL}")

    # Claim faucet
    faucet_result = await retry_operation(bot.claim_faucet, address, token, operation_name="Faucet")
    if faucet_result.get('data'):
        available_timestamp = faucet_result["data"].get("avaliable_timestamp")
        readable_time = datetime.fromtimestamp(available_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        log(f"{Fore.GREEN}Faucet already claimed! Next claim in {readable_time}{Style.RESET_ALL}")

    elif faucet_result and faucet_result.get("msg") == "ok":
        log(f"{Fore.GREEN}Faucet claimed: 0.2 PHRS{Style.RESET_ALL}")

    # Send to friends
    friends_count = config.get("friendsToSend", 0)
    if friends_count > 0:
        log(f"{Fore.BLUE}Sending to {friends_count} friends{Style.RESET_ALL}")
        for i in range(friends_count):
            receiver = bot.generate_random_receiver()
            amount = get_random_amount("sendAmount")
            balance = bot.get_balance(address, 'PHRS')

            # display
            log(f"{Fore.GREEN}Balance: {balance}{Style.RESET_ALL}")

            if balance <= amount:
                log(f"{Fore.YELLOW}Insufficient PHRS balance{Style.RESET_ALL}")
                break

            transfer_result = await retry_operation(bot.transfer, private_key, address, receiver, amount,
                                                    operation_name=f"Transfer {i + 1}")
            if transfer_result:
                tx_hash, block_number = transfer_result
                verify_result = await retry_operation(bot.verify_transfer, address, token, tx_hash,
                                                      operation_name="Verify transfer")
                if verify_result and verify_result.get("msg") == "task verified successfully":
                    log(f"{Fore.GREEN}Transfer {i + 1} verified: {amount} PHRS{Style.RESET_ALL}")
                    log(f"{Fore.CYAN}TX: https://testnet.pharosscan.xyz/tx/{tx_hash}{Style.RESET_ALL}")

                # Use timeout with logging for short delays
                time1, time2 = get_short_timeout()
                await timeout_with_log(time1, time2)

    # Wrap/Unwrap cycles
    wrap_cycles = config.get("wrapCycle", 0)
    if wrap_cycles > 0:
        log(f"{Fore.BLUE}Starting {wrap_cycles} wrap/unwrap cycles{Style.RESET_ALL}")
        for i in range(wrap_cycles):
            amount = get_random_amount("wrapAmount")

            # Wrap
            balance = bot.get_balance(address, 'PHRS')
            if balance > amount:
                wrap_result = await retry_operation(bot.wrap_unwrap, private_key, address, amount, True,
                                                    operation_name=f"Wrap {i + 1}")
                if wrap_result:
                    log(f"{Fore.GREEN}Wrapped {amount} PHRS to WPHRS{Style.RESET_ALL}")
                    time1, time2 = get_short_timeout()
                    await timeout_with_log(time1, time2)

            # Unwrap
            wphrs_balance = bot.get_balance(address, 'WPHRS')
            if wphrs_balance > amount:
                unwrap_result = await retry_operation(bot.wrap_unwrap, private_key, address, amount, False,
                                                      operation_name=f"Unwrap {i + 1}")
                if unwrap_result:
                    log(f"{Fore.GREEN}Unwrapped {amount} WPHRS to PHRS{Style.RESET_ALL}")
                    time1, time2 = get_short_timeout()
                    await timeout_with_log(time1, time2)

    # Swap cycles
    swap_cycles = config.get("swapCycle", 0)
    if swap_cycles > 0:
        log(f"{Fore.BLUE}Starting {swap_cycles} swap cycles{Style.RESET_ALL}")
        for i in range(swap_cycles):
            # WPHRS to USDC
            wphrs_balance = bot.get_balance(address, 'WPHRS')
            if wphrs_balance > 0.005:
                swap_result = await retry_operation(bot.swap_tokens, private_key, address, 'WPHRS', 'USDC', 0.005,
                                                    operation_name=f"Swap WPHRS->USDC {i + 1}")
                if swap_result:
                    log(f"{Fore.GREEN}Swapped 0.005 WPHRS to USDC{Style.RESET_ALL}")
                    # Longer timeout for swaps
                    timeout_range = config.get("shortTimeout", [5, 20])
                    await timeout_with_log(timeout_range[0] * 2, timeout_range[1] * 2)

            # USDC to WPHRS
            usdc_balance = bot.get_balance(address, 'USDC')
            if usdc_balance > 1.5:
                swap_result = await retry_operation(bot.swap_tokens, private_key, address, 'USDC', 'WPHRS', 1.5,
                                                    operation_name=f"Swap USDC->WPHRS {i + 1}")
                if swap_result:
                    log(f"{Fore.GREEN}Swapped 1.5 USDC to WPHRS{Style.RESET_ALL}")
                    # Longer timeout for swaps
                    timeout_range = config.get("shortTimeout", [5, 20])
                    await timeout_with_log(timeout_range[0] * 2, timeout_range[1] * 2)