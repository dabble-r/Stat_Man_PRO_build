# GitHub Authentication Guide

## Current Issue
You're getting a 401 authentication error when trying to push to GitHub. This is because GitHub no longer accepts passwords for HTTPS authentication.

## Solution Options

### Option 1: Personal Access Token (PAT) with HTTPS (Recommended)

#### Step 1: Create a Personal Access Token
1. Go to GitHub.com → Your Profile → Settings
2. Click "Developer settings" (bottom left)
3. Click "Personal access tokens" → "Tokens (classic)"
4. Click "Generate new token" → "Generate new token (classic)"
5. Give it a name (e.g., "Stat_Man_PRO_build")
6. Select expiration (recommend 90 days or custom)
7. **Check the `repo` scope** (gives full access to repositories)
8. Click "Generate token"
9. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)

#### Step 2: Use the Token
When you push, use the token as your password:
```bash
git push origin master
# Username: your-github-username
# Password: paste-your-token-here (NOT your GitHub password)
```

#### Step 3: Store Credentials (Optional but Recommended)
To avoid entering the token every time:

**Linux/WSL:**
```bash
# Install Git credential helper
git config --global credential.helper store

# Or use cache (stores for 1 hour)
git config --global credential.helper cache
git config --global credential.helper 'cache --timeout=3600'
```

After first push with token, Git will remember it.

---

### Option 2: SSH Authentication (More Secure)

#### Step 1: Generate SSH Key
```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Press Enter to accept default location
# Optionally set a passphrase for extra security
```

#### Step 2: Add SSH Key to GitHub
```bash
# Copy your public key
cat ~/.ssh/id_ed25519.pub
# Copy the entire output
```

Then:
1. GitHub → Settings → SSH and GPG keys
2. Click "New SSH key"
3. Paste your public key
4. Click "Add SSH key"

#### Step 3: Change Remote to SSH
```bash
# Change remote URL from HTTPS to SSH
git remote set-url origin git@github.com:dabble-r/Stat_Man_PRO_build.git

# Verify
git remote -v
```

#### Step 4: Test SSH Connection
```bash
ssh -T git@github.com
# Should see: "Hi username! You've successfully authenticated..."
```

#### Step 5: Push
```bash
git push origin master
# No password needed!
```

---

### Option 3: GitHub CLI (gh)

Install GitHub CLI and authenticate:
```bash
# Install gh (if not installed)
# Ubuntu/WSL:
sudo apt update
sudo apt install gh

# Authenticate
gh auth login
# Follow prompts to authenticate

# Then push normally
git push origin master
```

---

## Quick Fix (Temporary)

If you just need to push once right now:

1. **Get a Personal Access Token** (see Option 1, Step 1)
2. **Push with token:**
   ```bash
   git push origin master
   # When prompted:
   # Username: your-github-username
   # Password: paste-your-token-here
   ```

---

## Troubleshooting

### "Permission denied" or "Access denied"
- Make sure you have write access to the repository
- Check that your token has the `repo` scope
- Verify you're using the correct GitHub username

### "Repository not found"
- Check the repository URL is correct
- Verify you have access to the repository
- Make sure you're authenticated with the correct GitHub account

### Token expired
- Generate a new token
- Update stored credentials:
  ```bash
  git credential reject
  # Then push again and enter new token
  ```

---

## Security Notes

- **Never commit tokens to your repository**
- Tokens are like passwords - keep them secret
- Use SSH keys for better security (Option 2)
- Consider using environment variables for CI/CD

---

## Recommended Approach

For development, I recommend **Option 2 (SSH)** because:
- More secure (no tokens to manage)
- No password prompts after setup
- Works seamlessly with GitHub
- Better for long-term use

For quick one-time pushes, use **Option 1 (PAT)**.
