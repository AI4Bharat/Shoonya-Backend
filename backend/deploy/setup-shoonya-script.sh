os=$(uname)

if [ "$os" = "Linux" ] || [ "$os" = "Darwin" ]; then

git clone https://github.com/AI4Bharat/Shoonya-Backend.git
cd Shoonya-Backend
git checkout dev
git pull origin dev
cp .env.example ./backend/.env
cd backend
python3 -m venv  venv
source venv/bin/activate

pip install -r ./deploy/requirements.txt

new_secret_key=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

env_file=".env"
if sed --version 2>&1 | grep -q 'GNU sed'; then
  sed -i "/^SECRET_KEY=/d" "$env_file"
else
  sed -i.bak "/^SECRET_KEY=/d" "$env_file"
  rm -f "$env_file.bak"
fi

echo "SECRET_KEY='$new_secret_key'" >> "$env_file"

echo "New secret key has been generated and updated in $env_file"

else
  echo "Cannot run this script on: $os"
fi

