cmake_minimum_required(VERSION 3.20)

project(resolve_aio_ofx LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN ON)

if(NOT DEFINED OFX_SDK_ROOT)
    message(FATAL_ERROR "Set OFX_SDK_ROOT to the OpenFX SDK root before configuring this target.")
endif()

set(OFX_INCLUDE_DIR "${OFX_SDK_ROOT}/include")
if(NOT EXISTS "${OFX_INCLUDE_DIR}/ofxImageEffect.h")
    message(FATAL_ERROR "Could not find ofxImageEffect.h under ${OFX_INCLUDE_DIR}")
endif()

add_library(resolve_aio_ofx MODULE
    plugin_host.cpp
    effects/ResolveAIODemoEffect.cpp
)

target_include_directories(resolve_aio_ofx
    PRIVATE
        "${OFX_INCLUDE_DIR}"
        "${CMAKE_CURRENT_SOURCE_DIR}/effects"
)

target_compile_definitions(resolve_aio_ofx
    PRIVATE
        OFX_PLUGIN_VERSION_MAJOR=1
        OFX_PLUGIN_VERSION_MINOR=0
)

set_target_properties(resolve_aio_ofx PROPERTIES
    OUTPUT_NAME "ResolveAIOOFX"
    PREFIX ""
)
