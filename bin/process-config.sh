if [ -d "$SRC_DIR/ckan/ckanext/activity" ]; then
    sed -i 's|^ckan.plugins =|ckan.plugins = activity|' $CKAN_INI
    sed -i 's|^ckan.plugins =|ckan.plugins = activity|' .docker/test.ini
fi

