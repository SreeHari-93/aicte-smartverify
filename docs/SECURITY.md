# AICTE SmartVerify AI - Security Model & Specifications

## 1. Cryptographic Standards & Password Policy

### 1.1 Password Hashing (Argon2id)
All user passwords are stored using the state-of-the-art **Argon2id** algorithm (`time_cost=3`, `memory_cost=64MB`, `parallelism=4`). Argon2id provides exceptional resistance against both GPU-based brute-force attacks and side-channel timing analysis.

### 1.2 Password Complexity Policy
Passwords enforced during registration and onboarding must satisfy:
- Minimum length of 8 characters
- At least one uppercase Latin character (`A-Z`)
- At least one lowercase Latin character (`a-z`)
- At least one numerical digit (`0-9`)
- At least one special symbol (`!@#$%^&*(),.?":{}|<>-=_`)

---

## 2. Prevention of User Enumeration & Timing Attacks

- **Constant-Time Verification**: When an unrecognized user identifier or Institute ID is provided, the authentication service executes a dummy verification pass against a pre-hashed placeholder (`DUMMY_PASSWORD_HASH`). This ensures response latency remains uniform whether the user exists or not.
- **Generic Responses**: All failure responses return a uniform error payload: `"Invalid credentials. Please verify your details and password."`

---

## 3. Dynamic Captcha Mechanism

- **Client-Side Generation Strictly Prohibited**: The captcha is generated dynamically on the server using Pillow with background noise, interference lines, and character rotation.
- **Storage Strategy**: The server **never** stores the plain text of the captcha. Only the SHA-256 hash of the normalized (uppercase) challenge is stored in `captcha_challenges`.
- **Short TTL**: The challenge has an absolute TTL of 120 seconds (2 minutes).
- **One-Time Use (Non-Replayability)**: The verification method marks `used = True` immediately upon the first evaluation attempt, preventing replay attacks.

---

## 4. Rate Limiting & Account Lockout Defense

- **Sliding-Window Rate Limiting**:
  - Max **5 attempts per minute per IP address**. Exceeding triggers HTTP `429 Too Many Requests` with a `Retry-After` header.
  - Max **5 attempts per minute per targeted account**.
- **15-Minute Account Lockout**:
  - After **5 consecutive failed password attempts**, the account `locked_until` timestamp is set to `now + 15 minutes`.
  - Any subsequent attempts during this window return HTTP `423 Locked` with a precise countdown payload for user feedback.

---

## 5. Token Architecture & Cookie Security

- **Access Token**: Short-lived JWT (15-minute expiration) containing `sub` (user ID), `role`, and `jti` claim.
- **Refresh Token**: High-entropy cryptographically random string (48 bytes URL-safe). Stored in the database as a SHA-256 hash.
- **Refresh Token Rotation**: Each token refresh permanently revokes the old refresh token record (`revoked = True`) and issues a brand new pair.
- **Cookie Flags**:
  - `HttpOnly`: Mitigates script access and XSS theft.
  - `SameSite=Strict` / `Lax`: Protects against Cross-Site Request Forgery.
  - `Secure`: Transmitted only over HTTPS in production.

---

## 6. CSRF Protection (Double-Submit Token)

State-changing endpoints (`POST`, `PUT`, `DELETE`) require the client to supply an `X-CSRF-Token` HTTP header matching the value stored in the `aicte_csrf_token` cookie. The backend performs a constant-time comparison (`secrets.compare_digest`).

---

## 7. Append-Only Audit Logging

All security-relevant actions are recorded in the `audit_logs` table:
- Actions tracked: `LOGIN_SUCCESS`, `LOGIN_FAILURE`, `CAPTCHA_FAILURE`, `ACCOUNT_LOCKOUT`, `LOGIN_BLOCKED_LOCKED`, `RATE_LIMITED_IP`, `RATE_LIMITED_ACCOUNT`, `LOGOUT`, `TOKEN_REFRESH`, `REGISTER`.
- Metadata logged: `user_id`, `role`, `ip_address`, `user_agent`, `reason`, `timestamp`.
- Architecture: The table is **append-only**. The ORM exposes no update or delete routes, ensuring an immutable trail for forensic compliance.

