set -euo pipefail

# CONFIGURE UEL
GITHUB_SSH_URL="git@github.com:SinitinVladimir/Tools.git"

echo "Step 1: Removing any existing 'origin' remote..."
if git remote get-url origin >/dev/null 2>&1; then
  git remote remove origin
  echo "   Removed old origin"
else
  echo "   No existing origin to remove"
fi

echo "Step 2: Adding new origin: $GITHUB_SSH_URL"
git remote add origin "$GITHUB_SSH_URL"
git remote -v

# Check for existing SSH key
KEY_PATH="$HOME/.ssh/id_ed25519"
PUB_KEY_PATH="$KEY_PATH.pub"

if [ -f "$PUB_KEY_PATH" ]; then
  echo "Step 3: SSH key already exists at $PUB_KEY_PATH"
else
  echo "Step 3: No SSH key found. Generating one now..."
  ssh-keygen -t ed25519 -C "vladi@oldVibe" -f "$KEY_PATH" -N ""
  echo "   Generated SSH key pair"
fi

echo "Step 4: Starting ssh-agent and adding your key..."
eval "$(ssh-agent -s)"
ssh-add "$KEY_PATH"

echo
echo "Your public key is:"
echo "----------------------------------------"
cat "$PUB_KEY_PATH"
echo "----------------------------------------"
echo
echo "Copy the above key and add it to your GitHub account:"
echo "  1. Go to https://github.com/settings/keys"
echo "  2. Click 'New SSH key', paste it, and save."
read -p "Press Enter once you have added the key to GitHub..."

echo "Step 5: Testing SSH connection to GitHub..."
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
  echo "   SSH authentication successful"
else
  echo "   SSH test failed. Check your key on GitHub and try again"
  exit 1
fi

echo "Step 6: Pushing 'main' branch to GitHub..."
git push -u origin main

echo
echo "All done. Your code is now on GitHub."
