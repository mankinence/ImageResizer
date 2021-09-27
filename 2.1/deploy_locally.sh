TARGET_DIR=$HOME/Library/Application\ Support/Anki2/addons21/1214357311
rm -rf "${TARGET_DIR:?}"/*
cp -r __init__.py PIL "${TARGET_DIR}"