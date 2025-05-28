# **Pharos Testnet Bot**

Automate your farming on the Pharos Testnet with this bot! It performs key actions like claiming faucet, checking in, wrapping, swapping, and sending tokens to friends using randomized configurations and proxy support.

> 📝 **Start Here First:**
> 👉 [Sign up on Pharos Testnet](https://testnet.pharosnetwork.xyz/experience?inviteCode=ugYFqJDzaEXkyhAR)
> 🔗 Bind your **X (Twitter)** account to enable faucet claiming and interaction features.

---

## 🚀 Features

* Wrap, swap, and send PHRS tokens.
* Faucet claiming and check-in automation.
* Supports randomized wrapping/sending values.
* Private proxy support (recommended).
* Multi-account support using `accounts.txt`.

---

## ⚙️ Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Anzywiz/pharos-testnet-bot.git
cd pharos-testnet-bot
```

### 2️⃣ Create and Activate a Virtual Environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Requirements

```bash
pip install -r requirements.txt
```

---

## 🗂 Files to Create

### ✅ `accounts.txt`

Add one **private key per line**:

```
your_private_key_1
your_private_key_2
```

### ✅ `proxy.txt` (if using proxyType 2)

Here are a few proxy formats
```
ip:port
protocol://ip:port
protocol://user:pass@ip:port
```

---

## ⚙️ config.json Format

Here’s a sample `config.json`:

```json
{
  "referralCode": "ugYFqJDzaEXkyhAR",
  "swapCycle": 1,
  "wrapCycle": 1,
  "wrapAmount": [0.001, 0.009],
  "friendsToSend": 5,
  "sendAmount": [0.001, 0.005],
  "useProxy": true,
  "proxyType": 2,
  "rotateProxy": true,
  "waitTime": 86400
}
```

---

## 🧾 Config Field Descriptions

| Key             | Description                                                                                                                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `referralCode`  | Invite code used in the referral URL.                                                                                                                                                             |
| `swapCycle`     | Number of swap actions (PHRS to USDT or USDT to PHRS).                                                                                                                                            |
| `wrapCycle`     | Number of times to wrap and unwrap PHRS.                                                                                                                                                          |
| `wrapAmount`    | Min-max range for random wrap amount. Example: `[0.001, 0.009]`.                                                                                                                                  |
| `friendsToSend` | Number of friends to send tokens to.                                                                                                                                                              |
| `sendAmount`    | Range for random amount to send. Example: `[0.001, 0.005]`.                                                                                                                                       |
| `useProxy`      | `true` to enable proxy use, `false` to disable.                                                                                                                                                   |
| `proxyType`     | `1` = Use free proxies from [Monosans](https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt) *(not recommended)*. <br>`2` = Use your private proxies listed in `proxy.txt`. |
| `rotateProxy`   | `true` to rotate proxies between accounts.                                                                                                                                                        |
| `waitTime`      | Seconds to wait before next run (after all accounts).                                                                                                                                             |

---

## ▶️ Running the Bot

```bash
python main.py
```

---

## 🔄 Updating

```bash
git pull
```

---

## 💡 Tips

* Make sure your Twitter/X account is bound to the Pharos profile.
* Free proxies are unstable—**private proxies are highly recommended**.
* Review and adjust `wrapAmount` and `sendAmount` to suit your farming strategy.

---

## 🛠 Issues & Contributions

* Found a bug? Open an issue.
* Want to contribute? Fork the repo, make changes, and submit a pull request.
