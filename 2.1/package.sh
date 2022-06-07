TARGET_DIR=/tmp/image_resizer
rm -rf ${TARGET_DIR}
mkdir ${TARGET_DIR}
cp -r __init__.py resizer ${TARGET_DIR}
pushd ${TARGET_DIR} || exit
zip -r ../image_resizer.ankiaddon *
rm -rf ${TARGET_DIR:?}/*
mv ../image_resizer.ankiaddon ${TARGET_DIR}

echo "The addon has been packaged to ${TARGET_DIR}/image_resizer.ankiaddon"
popd || exit
