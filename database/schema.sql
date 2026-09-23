-- =============================================================
-- SentinelBank AI – Full MySQL 8 Schema
-- Engine: InnoDB | Charset: utf8mb4 | Collation: utf8mb4_unicode_ci
-- =============================================================

SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS sentinelbank
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE sentinelbank;

-- -------------------------------------------------------------
-- 1. users
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone         VARCHAR(20)  DEFAULT NULL,
    role          ENUM('customer','bank_agent','admin') NOT NULL DEFAULT 'customer',
    mfa_enabled   TINYINT(1) NOT NULL DEFAULT 0,
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_users_email (email),
    KEY ix_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 2. customers
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id                 INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id            INT UNSIGNED NOT NULL,
    name               VARCHAR(255) NOT NULL,
    phone              VARCHAR(20)  DEFAULT NULL,
    preferred_language ENUM('en','kn','hi','ta','te','mr','bn','gu','pa') NOT NULL DEFAULT 'en',
    address            TEXT         DEFAULT NULL,
    city               VARCHAR(100) DEFAULT NULL,
    state              VARCHAR(100) DEFAULT NULL,
    aadhaar_masked     VARCHAR(20)  DEFAULT NULL,
    pan_masked         VARCHAR(12)  DEFAULT NULL,
    date_of_birth      DATE         DEFAULT NULL,
    occupation         VARCHAR(100) DEFAULT NULL,
    annual_income      DECIMAL(15,2) DEFAULT NULL,
    net_worth          DECIMAL(15,2) DEFAULT NULL,
    risk_profile       ENUM('conservative','moderate','aggressive') DEFAULT NULL,
    profile_image      VARCHAR(255) DEFAULT NULL,
    kyc_status         ENUM('pending','verified','rejected') NOT NULL DEFAULT 'pending',
    created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_customers_user_id (user_id),
    KEY ix_customers_user_id (user_id),
    CONSTRAINT fk_customers_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 3. accounts
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    customer_id    INT UNSIGNED NOT NULL,
    account_number VARCHAR(20)  NOT NULL,
    account_type   ENUM('savings','current','salary','nri','fixed_deposit') NOT NULL DEFAULT 'savings',
    balance        DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    currency       VARCHAR(10) NOT NULL DEFAULT 'INR',
    ifsc_code      VARCHAR(15)  DEFAULT NULL,
    branch         VARCHAR(100) DEFAULT NULL,
    is_active      TINYINT(1)  NOT NULL DEFAULT 1,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_accounts_number (account_number),
    KEY ix_accounts_customer_id (customer_id),
    CONSTRAINT fk_accounts_customer FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 4. loans
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS loans (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    customer_id   INT UNSIGNED NOT NULL,
    loan_type     ENUM('home','personal','vehicle','education','gold','business') NOT NULL DEFAULT 'personal',
    loan_amount   DECIMAL(15,2) NOT NULL,
    outstanding   DECIMAL(15,2) NOT NULL,
    interest_rate DECIMAL(5,2)  NOT NULL,
    tenure_months INT UNSIGNED  NOT NULL,
    start_date    DATE NOT NULL,
    end_date      DATE NOT NULL,
    status        ENUM('active','closed','defaulted','npa') NOT NULL DEFAULT 'active',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_loans_customer_id (customer_id),
    KEY ix_loans_status      (status),
    CONSTRAINT fk_loans_customer FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 5. autopays
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS autopays (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_id        INT UNSIGNED NOT NULL,
    payee_name        VARCHAR(200) NOT NULL,
    payee_account     VARCHAR(30)  DEFAULT NULL,
    amount            DECIMAL(15,2) NOT NULL,
    frequency         ENUM('daily','weekly','monthly','quarterly','annually') NOT NULL DEFAULT 'monthly',
    next_payment_date DATE NOT NULL,
    end_date          DATE DEFAULT NULL,
    status            ENUM('active','paused','cancelled') NOT NULL DEFAULT 'active',
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_autopays_account_id (account_id),
    KEY ix_autopays_status     (status),
    CONSTRAINT fk_autopays_account FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 6. transactions
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_id       INT UNSIGNED NOT NULL,
    amount           DECIMAL(15,2) NOT NULL,
    transaction_type ENUM('debit','credit') NOT NULL,
    description      VARCHAR(255) DEFAULT NULL,
    category         ENUM('transfer','food','shopping','utilities','emi','salary',
                          'investment','insurance','entertainment','travel',
                          'health','education','other') NOT NULL DEFAULT 'other',
    reference_id     VARCHAR(50)  DEFAULT NULL,
    merchant         VARCHAR(200) DEFAULT NULL,
    channel          ENUM('upi','neft','rtgs','imps','atm','pos','online','auto') NOT NULL DEFAULT 'online',
    timestamp        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    balance_after    DECIMAL(15,2) DEFAULT NULL,
    loan_id          INT UNSIGNED DEFAULT NULL,
    autopay_id       INT UNSIGNED DEFAULT NULL,
    KEY ix_transactions_account_id (account_id),
    KEY ix_transactions_timestamp  (timestamp),
    KEY ix_transactions_category   (category),
    CONSTRAINT fk_transactions_account FOREIGN KEY (account_id) REFERENCES accounts (id),
    CONSTRAINT fk_transactions_loan    FOREIGN KEY (loan_id)    REFERENCES loans    (id),
    CONSTRAINT fk_transactions_autopay FOREIGN KEY (autopay_id) REFERENCES autopays (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 7. emis
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emis (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    loan_id        INT UNSIGNED NOT NULL,
    installment_no INT UNSIGNED NOT NULL,
    due_date       DATE NOT NULL,
    principal      DECIMAL(15,2) NOT NULL,
    interest       DECIMAL(15,2) NOT NULL,
    total_amount   DECIMAL(15,2) NOT NULL,
    paid_amount    DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    paid_date      DATE DEFAULT NULL,
    status         ENUM('pending','paid','overdue','waived') NOT NULL DEFAULT 'pending',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_emis_loan_id  (loan_id),
    KEY ix_emis_due_date (due_date),
    KEY ix_emis_status   (status),
    CONSTRAINT fk_emis_loan FOREIGN KEY (loan_id) REFERENCES loans (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 8. credit_scores
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS credit_scores (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    customer_id INT UNSIGNED NOT NULL,
    score       SMALLINT UNSIGNED NOT NULL,
    bureau      VARCHAR(50) NOT NULL DEFAULT 'CIBIL',
    remarks     TEXT DEFAULT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_credit_scores_customer_id (customer_id),
    KEY ix_credit_scores_recorded_at (recorded_at),
    CONSTRAINT fk_credit_scores_customer FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 9. insurance_policies
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS insurance_policies (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    customer_id       INT UNSIGNED NOT NULL,
    policy_number     VARCHAR(30)  NOT NULL,
    policy_type       ENUM('life','health','vehicle','property','travel') NOT NULL,
    provider          VARCHAR(100) NOT NULL,
    sum_assured       DECIMAL(15,2) NOT NULL,
    premium_amount    DECIMAL(10,2) NOT NULL,
    premium_frequency ENUM('monthly','quarterly','annually') NOT NULL DEFAULT 'annually',
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    status            ENUM('active','expired','cancelled','lapsed') NOT NULL DEFAULT 'active',
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_insurance_policy_number (policy_number),
    KEY ix_insurance_customer_id (customer_id),
    KEY ix_insurance_status      (status),
    CONSTRAINT fk_insurance_customer FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 10. expense_splits
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expense_splits (
    id                    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    initiator_customer_id INT UNSIGNED NOT NULL,
    title                 VARCHAR(200) NOT NULL,
    description           TEXT DEFAULT NULL,
    total_amount          DECIMAL(15,2) NOT NULL,
    currency              VARCHAR(10) NOT NULL DEFAULT 'INR',
    status                ENUM('open','settled','partially_settled') NOT NULL DEFAULT 'open',
    created_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_expense_splits_initiator (initiator_customer_id),
    KEY ix_expense_splits_status    (status),
    CONSTRAINT fk_expense_splits_initiator FOREIGN KEY (initiator_customer_id) REFERENCES customers (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 11. expense_split_participants
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expense_split_participants (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    split_id     INT UNSIGNED NOT NULL,
    customer_id  INT UNSIGNED NOT NULL,
    share_amount DECIMAL(10,2) NOT NULL,
    paid         TINYINT(1)   NOT NULL DEFAULT 0,
    paid_at      DATETIME DEFAULT NULL,
    KEY ix_esp_split_id    (split_id),
    KEY ix_esp_customer_id (customer_id),
    CONSTRAINT fk_esp_split    FOREIGN KEY (split_id)    REFERENCES expense_splits (id) ON DELETE CASCADE,
    CONSTRAINT fk_esp_customer FOREIGN KEY (customer_id) REFERENCES customers      (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 12. notifications
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id    INT UNSIGNED NOT NULL,
    title      VARCHAR(200) NOT NULL,
    body       TEXT NOT NULL,
    notif_type ENUM('transaction','loan','security','system','fraud','otp') NOT NULL DEFAULT 'system',
    channel    ENUM('push','email','sms','in_app') NOT NULL DEFAULT 'in_app',
    is_read    TINYINT(1) NOT NULL DEFAULT 0,
    read_at    DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_notifications_user_id    (user_id),
    KEY ix_notifications_is_read    (is_read),
    KEY ix_notifications_created_at (created_at),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 13. fraud_logs
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fraud_logs (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT UNSIGNED DEFAULT NULL,
    customer_id    INT UNSIGNED NOT NULL,
    rule_triggered VARCHAR(100) NOT NULL,
    risk_score     DECIMAL(5,4) NOT NULL DEFAULT 0.0000,
    description    TEXT DEFAULT NULL,
    status         ENUM('flagged','reviewed','false_positive','confirmed_fraud') NOT NULL DEFAULT 'flagged',
    reviewed_by    INT UNSIGNED DEFAULT NULL,
    reviewed_at    DATETIME DEFAULT NULL,
    is_blocked     TINYINT(1) NOT NULL DEFAULT 0,
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_fraud_logs_transaction_id (transaction_id),
    KEY ix_fraud_logs_customer_id    (customer_id),
    KEY ix_fraud_logs_status         (status),
    KEY ix_fraud_logs_created_at     (created_at),
    CONSTRAINT fk_fraud_logs_transaction FOREIGN KEY (transaction_id) REFERENCES transactions (id),
    CONSTRAINT fk_fraud_logs_customer    FOREIGN KEY (customer_id)    REFERENCES customers    (id),
    CONSTRAINT fk_fraud_logs_reviewer    FOREIGN KEY (reviewed_by)    REFERENCES users        (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 14. audit_logs
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED DEFAULT NULL,
    action      VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50)  DEFAULT NULL,
    entity_id   INT UNSIGNED DEFAULT NULL,
    ip_address  VARCHAR(45)  DEFAULT NULL,
    user_agent  VARCHAR(500) DEFAULT NULL,
    details     TEXT         DEFAULT NULL,
    severity    ENUM('info','warning','critical') NOT NULL DEFAULT 'info',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_audit_logs_user_id    (user_id),
    KEY ix_audit_logs_action     (action),
    KEY ix_audit_logs_created_at (created_at),
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -------------------------------------------------------------
-- 15. sessions
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       INT UNSIGNED NOT NULL,
    refresh_token VARCHAR(512) NOT NULL,
    device_info   TEXT DEFAULT NULL,
    ip_address    VARCHAR(45) DEFAULT NULL,
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    expires_at    DATETIME NOT NULL,
    revoked_at    DATETIME DEFAULT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_sessions_refresh_token (refresh_token(255)),
    KEY ix_sessions_user_id       (user_id),
    KEY ix_sessions_is_active     (is_active),
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
