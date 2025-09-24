#!/bin/bash
set -e

# Create build directories
echo "Creating build directories..."
mkdir -p build/SDL2
mkdir -p build/freetype
mkdir -p prebuilt/linux/x86_64

# Build SDL2
echo "Building SDL2..."
cd build/SDL2
cmake ../../SDL2-2.32.4 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$PWD/../../prebuilt/linux/x86_64 \
  -DSDL_SHARED=ON \
  -DSDL_STATIC=ON \
  -DSDL_ALSA=ON \
  -DSDL_PULSEAUDIO=ON \
  -DSDL_X11=ON \
  -DSDL_WAYLAND=ON \
  -DSDL_OPENGL=ON \
  -DSDL_OPENGLES=ON \
  -DSDL_VULKAN=ON

make -j$(nproc)
make install

cd ../..

# Build FreeType
echo "Building FreeType..."
cd build/freetype
cmake ../../freetype-2.14.1 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$PWD/../../prebuilt/linux/x86_64 \
  -DBUILD_SHARED_LIBS=ON \
  -DFT_DISABLE_HARFBUZZ=ON \
  -DFT_DISABLE_BROTLI=ON

make -j$(nproc)
make install

cd ../..

# Create library info file
echo "Creating library info..."
cat > prebuilt/linux/x86_64/library_info.txt << EOF
Built on: $(date)
Platform: $(lsb_release -ds 2>/dev/null || echo "Linux")
SDL2 Version: 2.32.4
FreeType Version: 2.14.1

Libraries:
$(ls -la prebuilt/linux/x86_64/lib/)

Headers:
$(ls -la prebuilt/linux/x86_64/include/)
EOF

echo "Build complete!"
echo "=== Built libraries ==="
find prebuilt/linux/x86_64 -type f -name "*.so*" -o -name "*.a" | sort
echo ""
echo "=== Header directories ==="
ls -d prebuilt/linux/x86_64/include/*/ 2>/dev/null || ls prebuilt/linux/x86_64/include/