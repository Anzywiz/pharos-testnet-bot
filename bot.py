from utils import \
    PharosBot, log, Fore, Style, process_account, get_short_timeout, timeout_with_log, config, asyncio


async def main():
    try:
        with open('accounts.txt', 'r') as f:
            accounts = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        log(f"{Fore.RED}accounts.txt not found{Style.RESET_ALL}")
        return

    bot = PharosBot()
    await bot.load_proxies()

    log(f"{Fore.BLUE}Pharos Testnet Bot Started{Style.RESET_ALL}")
    log(f"{Fore.GREEN}Loaded {len(accounts)} accounts{Style.RESET_ALL}")

    while True:
        for private_key in accounts:
            if private_key:
                try:
                    address = bot.generate_address(private_key)
                    await process_account(bot, private_key, address)
                except Exception as e:
                    log(f"{Fore.RED}Account processing failed: {e}{Style.RESET_ALL}")

                # Short delay between accounts
                time1, time2 = get_short_timeout()
                await timeout_with_log(time1, time2)

        wait_time = config.get("waitTime", 86400)
        log(f"{Fore.CYAN}Cycle complete. Waiting {wait_time} seconds...{Style.RESET_ALL}")
        await timeout_with_log(wait_time, wait_time)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log(f"{Fore.RED}Bot stopped by user{Style.RESET_ALL}")