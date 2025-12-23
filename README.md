# Snowflake QA Bot — Docker + AWS Elastic Beanstalk Deployment Guide

This repository contains a minimal Streamlit QA web app that uses Snowflake and Cortex to convert natural language questions into SQL, execute them against a read-only execution view, and display results.

Important security note: Snowflake credentials MUST stay on the server and never be exposed to users or the UI.

Contents
- `Dockerfile`
- `app.py` (Streamlit application)
- `requirements.txt`

What we are building

1. User enters a natural language question in the Streamlit UI (for example: "Which customer has the highest total sales?").
2. Streamlit forwards the query to Cortex for NL→SQL translation.
3. Cortex generates SQL (using semantic views for understanding).
4. The app executes generated SQL only against a dedicated execution VIEW in Snowflake.
5. Results are displayed to the user.

Preconditions — Snowflake objects that MUST exist

Create these objects in your Snowflake account BEFORE deploying the app:

- Database: `DEMO_DB`
- Schema: `PUBLIC`
- Warehouse: `DEMO_WH`
- Tables: `CUSTOMERS`, `SALES`
- Relationship: `SALES.CUSTOMER_ID = CUSTOMERS.CUSTOMER_ID`

Execution view (what the app is allowed to query)

Snowflake Semantic Views are used only for Cortex's understanding but cannot be queried directly with SELECT. Therefore create a normal SQL view that the app will execute against.

Run this once in Snowflake (Worksheet):

```sql
CREATE OR REPLACE VIEW DEMO_DB.PUBLIC.SHIVANSHI_EXEC_VIEW AS
SELECT
  c.CUSTOMER_ID,
  c.CUSTOMER_NAME,
  s.ORDER_ID,
  s.ORDER_DATE,
  s.AMOUNT
FROM DEMO_DB.PUBLIC.SALES s
INNER JOIN DEMO_DB.PUBLIC.CUSTOMERS c
  ON s.CUSTOMER_ID = c.CUSTOMER_ID;
```

Security — create a read-only role for the app

Create a role that only has SELECT/USAGE privileges needed for the app (least privilege):

```sql
CREATE ROLE IF NOT EXISTS SPCS_AGENT_ROLE;

GRANT USAGE ON DATABASE DEMO_DB TO ROLE SPCS_AGENT_ROLE;
GRANT USAGE ON SCHEMA DEMO_DB.PUBLIC TO ROLE SPCS_AGENT_ROLE;

GRANT SELECT ON TABLE DEMO_DB.PUBLIC.CUSTOMERS TO ROLE SPCS_AGENT_ROLE;
GRANT SELECT ON TABLE DEMO_DB.PUBLIC.SALES TO ROLE SPCS_AGENT_ROLE;
GRANT SELECT ON VIEW DEMO_DB.PUBLIC.SHIVANSHI_EXEC_VIEW TO ROLE SPCS_AGENT_ROLE;

GRANT USAGE ON WAREHOUSE DEMO_WH TO ROLE SPCS_AGENT_ROLE;
GRANT USAGE ON INTEGRATION CORTEX TO ROLE SPCS_AGENT_ROLE;

GRANT ROLE SPCS_AGENT_ROLE TO USER YOUR_SNOWFLAKE_USER;
```

Replace `YOUR_SNOWFLAKE_USER` with the Snowflake user that the application will use.

Files required in this repo (exact)

The app requires exactly these three files at the repository root. Do not nest them inside another folder in the ZIP uploaded to Elastic Beanstalk.

- `Dockerfile` — Dockerfile to run Streamlit
- `app.py` — Streamlit application (already present)
- `requirements.txt` — dependencies (exact content required)

requirements.txt (exact content)

```
streamlit
snowflake-snowpark-python[pandas]
pandas
```

`app.py`

The included `app.py` implements the Streamlit UI and logic:

- Validates user input (minimum 4 words)
- Disables Snowflake caching in the app
- Uses Cortex to generate SQL
- Executes SQL only against the execution view `DEMO_DB.PUBLIC.SHIVANSHI_EXEC_VIEW`

No changes required to `app.py` if you followed the repository layout.

Dockerfile (exact content)

```
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

CMD ["streamlit", "run", "app.py", "--server.port=8000", "--server.address=0.0.0.0"]
```

Why Docker is required

Streamlit is not a WSGI app. Elastic Beanstalk's default Python platform expects WSGI apps served by a web server. Running inside Docker allows Streamlit to be started directly without WSGI/Gunicorn/Nginx and avoids 502 errors.

GitHub repository

1. Create a GitHub repo (example name: `SnowflakeAgentDocker`).
2. Commit and push these files (Dockerfile, app.py, requirements.txt, README.md) at the repo root.
3. The ZIP you upload to Elastic Beanstalk must contain Dockerfile at the root — no nested folders.

AWS Elastic Beanstalk — UI steps (short)

1. Login to AWS Console → Elastic Beanstalk → Create Application.
2. Configure Environment:
   - Application name: `SnowflakeAgent`
   - Environment tier: Web server environment
   - Platform: Docker
   - Platform version: Docker running on 64bit Amazon Linux 2023
   - Upload code: ZIP of the repo (Dockerfile at root)

3. Service access:
   - Service role: `aws-elasticbeanstalk-service-role`
   - EC2 instance profile: `aws-elasticbeanstalk-ec2-role`
   - Key pair: None required

4. Networking:
   - Public IP: Enable
   - VPC: Default
   - Subnets: Leave empty (use defaults)

5. Instance & scaling:
   - Environment type: Single instance
   - Instance type: `t3.micro`
   - Architecture: `x86_64`

6. Updates, logs, platform software:
   - Proxy server: NONE
   - Do NOT set a WSGI path or use Nginx proxy — Docker handles serving.

Environment variables (CRITICAL)

After creating the environment, go to Configuration → Environment properties and add EXACT keys (replace values with your credentials):

- `SNOWFLAKE_ACCOUNT` = your_account_identifier
- `SNOWFLAKE_USER` = your_user
- `SNOWFLAKE_PASSWORD` = your_password
- `SNOWFLAKE_ROLE` = SPCS_AGENT_ROLE

Save and create the environment. Wait 5–10 minutes — the health should become `OK` (one health warning is normal initially).

Verify the application

Open the environment URL (example):

```
http://SnowflakeAgent.us-east-1.elasticbeanstalk.com
```

You should see the QA Bot UI. Try a question like:

```
Which customer has the highest total sales
```

The result should return a table with the customer(s) and totals.

Notes & troubleshooting

- If you want to use SSH/SSH keys to push to GitHub, change the `origin` remote to the SSH URL: `git remote set-url origin git@github.com:username/repo.git`.
- Keep credentials secret and use environment variables only in Elastic Beanstalk configuration, not in code.
- If you see errors related to WSGI or Gunicorn, confirm you used the Docker platform and uploaded a ZIP with `Dockerfile` at the root.

Optional next steps (suggested)

- Add a `.gitignore` to exclude caches and local artifacts.
- Add a simple CI workflow (GitHub Actions) that builds the Docker image or runs lints.
- Add a short CONTRIBUTING.md describing how to run locally and how to add changes.

---

If you want, I can:

- Add a `.gitignore` and commit it.
- Switch remote to SSH for you.
- Create a GitHub Actions workflow to build and test the image.

Let me know which of those you want next.
