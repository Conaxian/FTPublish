temp=$(realpath "$0")
path=$(dirname "$temp")

python $path/ftp.py
