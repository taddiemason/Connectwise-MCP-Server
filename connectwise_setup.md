# ConnectWise API Credentials Setup Guide

This guide walks you through obtaining your ConnectWise API credentials step-by-step.

## 📋 What You'll Need

By the end of this guide, you'll have these three values for your `.env` file:

1. **CW_COMPANY_ID** - Your company identifier
2. **CW_PUBLIC_KEY** - Your public API key
3. **CW_PRIVATE_KEY** - Your private API key

---

## Step 1: Find Your Company ID

### Method A: From Your URL
When you log in to ConnectWise, look at the URL in your browser:

```
https://acmetechsolutions.myconnectwise.net/v2023_2/...
         ^^^^^^^^^^^^^^^^^
         This is your Company ID
```

**Example URLs:**
- `https://techcorp.myconnectwise.net/...` → Company ID: `techcorp`
- `https://acme.myconnectwise.net/...` → Company ID: `acme`
- `https://cw.yourcompany.com/...` → Company ID: Check System settings

### Method B: From System Settings
1. Log in to ConnectWise Manage
2. Click **System** in the top menu
3. Go to **Setup Tables** → **Company**
4. Look for "Company Identifier" field

---

## Step 2: Generate API Keys

### Option A: Using Your Own Account (Quick Start)

⚠️ **Warning:** This uses your personal credentials. For production, use Option B (API Member) instead.

1. **Log in to ConnectWise Manage**

2. **Open Your Account Settings**
   - Click your profile icon (top-right corner)
   - Select **"My Account"**

3. **Navigate to API Keys**
   - Click the **"API Keys"** tab
   - You'll see a list of existing keys (if any)

4. **Create New API Keys**
   - Click the **"+ New"** or **"Add"** button
   - A description field may appear (optional)
   - Enter a description: `MCP Server - Read Only`

5. **Copy Your Keys**
   ```
   Public Key:  A1B2C3D4E5F6G7H8I9J0
   Private Key: x9y8z7w6v5u4t3s2r1q0p9o8n7m6
   ```
   
   ⚠️ **IMPORTANT:** 
   - Copy both keys immediately
   - The Private Key will **NEVER** be shown again
   - Store them in a password manager

### Option B: Using API Member (Recommended for Production)

This method creates a dedicated API-only account with specific permissions.

1. **Navigate to Members**
   - Click **System** in the top menu
   - Select **Members**

2. **Create New API Member**
   - Click **"+ New"** or **"Add Member"**
   - Fill in the form:
     - **Identifier:** `mcp-readonly-api`
     - **Name:** `MCP Read-Only API`
     - **Member Type:** Select **"API Member"** or **"Integration"**
     - **Email:** Your admin email
     - **Default Location:** Select your location
     - **Default Department:** Select appropriate department

3. **Set Permissions (Read-Only)**
   - Go to the **Security Roles** tab
   - Assign appropriate read-only roles:
     - ✅ View Tickets
     - ✅ View Companies
     - ✅ View Contacts
     - ✅ View Opportunities
     - ✅ View Projects
     - ✅ View Time Entries
     - ✅ View Agreements
     - ❌ NO write/edit/delete permissions

4. **Generate API Keys**
   - Click **"API Keys"** tab
   - Click **"+ New"** or **"Generate Keys"**
   - Description: `MCP Server Integration`
   - Copy both Public and Private keys

5. **Verify Member is Active**
   - Ensure **"Inactive"** checkbox is NOT checked
   - Save the member

---

## Step 3: Determine Your API URL

### For Cloud-Hosted ConnectWise

Choose based on your region:

| Region | API URL |
|--------|---------|
| 🇺🇸 North America | `https://api-na.myconnectwise.net` |
| 🇪🇺 Europe | `https://api-eu.myconnectwise.net` |
| 🇦🇺 Australia | `https://api-au.myconnectwise.net` |

**How to determine your region:**
- Look at your login URL
- If it's `yourcompany.myconnectwise.net`, you're likely North America
- If it's `yourcompany-eu.myconnectwise.net`, you're Europe
- If it's `yourcompany-au.myconnectwise.net`, you're Australia

### For On-Premise Installation

Use your server's URL:
```
https://cw.yourcompany.com
```

Or your server's IP:
```
https://192.168.1.100
```

---

## Step 4: Find Your API Version

1. **Log in to ConnectWise Manage**

2. **Check the Version**
   - Look at the URL: `https://company.myconnectwise.net/v2023_2/...`
   - The version is: `v2023.2` (replace underscore with dot)
   
   OR
   
   - Click **System** → **About**
   - Look for version number
   - Convert to API version format:
     - `2023.2` → `v2023.2`
     - `2022.1` → `v2022.1`

**Common versions:**
- `v2023.2`
- `v2023.1`
- `v2022.2`
- `v2022.1`

---

## Step 5: Create Your .env File

Now that you have all the information, create your `.env` file:

```bash
# Copy the example file
cp .env.example .env

# Edit with your favorite editor
nano .env
# or
vim .env
```

Fill in your values:

```env
# Your actual credentials
CW_COMPANY_ID=acmetechsolutions
CW_PUBLIC_KEY=A1B2C3D4E5F6G7H8I9J0
CW_PRIVATE_KEY=x9y8z7w6v5u4t3s2r1q0p9o8n7m6

# Your region/server
CW_API_URL=https://api-na.myconnectwise.net

# Your version
CW_API_VERSION=v2023.2

# These can stay as defaults
CW_CLIENT_ID=mcp-connectwise-server
MCP_PORT=3002
LOG_LEVEL=INFO
```

**Save and close the file.**

---

## Step 6: Verify Your Configuration

### Test 1: Check File Permissions
```bash
# Make .env readable only by you
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw------- (owner read/write only)
```

### Test 2: Start the Server
```bash
./setup.sh
# Select option 1 to start
```

### Test 3: Check Health
```bash
curl http://localhost:3002/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "connectwise-mcp-bridge"
}
```

### Test 4: Run Full Test Suite
```bash
./test.sh
```

This will verify:
- ✅ Configuration file exists
- ✅ Docker is running
- ✅ Containers are healthy
- ✅ API authentication works
- ✅ No critical errors

---

## 🚨 Troubleshooting

### "Authentication Failed" Error

**Check these:**
1. Company ID is correct (check URL)
2. Public Key copied correctly (no extra spaces)
3. Private Key copied correctly (no extra spaces)
4. API Member is active (not disabled)
5. API Member has read permissions

**Test manually:**
```bash
# Replace with your values
COMPANY_ID="yourcompany"
PUBLIC_KEY="yourpublickey"
PRIVATE_KEY="yourprivatekey"

# Create auth string
AUTH=$(echo -n "${COMPANY_ID}+${PUBLIC_KEY}:${PRIVATE_KEY}" | base64)

# Test API
curl -H "Authorization: Basic ${AUTH}" \
     -H "clientId: test" \
     "https://api-na.myconnectwise.net/v2023.2/apis/3.0/system/info"
```

If this works, your credentials are correct!

### "Connection Refused" Error

**Check these:**
1. API URL is correct for your region
2. Your network allows outbound HTTPS
3. Firewall isn't blocking Docker
4. ConnectWise server is accessible

### Private Key Not Showing

⚠️ **You can only see the Private Key ONCE** when it's generated.

**If you lost it:**
1. Delete the old API key
2. Generate a new one
3. Copy both keys immediately
4. Store in password manager

---

## 🔒 Security Best Practices

1. **Never Share Keys**
   - Don't email them
   - Don't put in Slack
   - Don't commit to Git

2. **Use API Members**
   - Don't use personal accounts
   - Create dedicated API members
   - Set minimal permissions

3. **Rotate Keys Regularly**
   - Generate new keys quarterly
   - Delete old keys after rotation
   - Update .env file

4. **Monitor Usage**
   - Check API logs in ConnectWise
   - Monitor for unusual activity
   - Set up alerts if available

5. **Secure the .env File**
   ```bash
   chmod 600 .env
   ```

---

## 📚 Additional Resources

- [ConnectWise Developer Portal](https://developer.connectwise.com/)
- [ConnectWise REST API Documentation](https://developer.connectwise.com/Products/Manage/REST)
- [ConnectWise API Best Practices](https://developer.connectwise.com/Best_Practices)

---

## ✅ Checklist

Before starting the server, verify you have:

- [ ] Company ID confirmed
- [ ] Public Key copied and saved
- [ ] Private Key copied and saved
- [ ] API URL identified
- [ ] API Version determined
- [ ] .env file created
- [ ] .env file permissions set (chmod 600)
- [ ] Docker installed and running
- [ ] Port 3002 available (or changed in config)

**All set?** Run `./setup.sh` and select option 1 to start! 🚀

---

Need help? Check the main [README.md](README.md) or [quickstart.md](quickstart.md)
