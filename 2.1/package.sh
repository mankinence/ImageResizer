TARGET_DIR=/tmp/image_resizer
rm -rf ${TARGET_DIR}
mkdir ${TARGET_DIR}
cp -r resizer/* PIL ${TARGET_DIR}
pushd ${TARGET_DIR} || exit
zip -r ../image_resizer.ankiaddon *

echo "The addon has been packaged to ${TARGET_DIR}/image_resizer.ankiaddon"
popd || exit
