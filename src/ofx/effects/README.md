# OFX Effects

This directory now contains the first OpenFX scaffold for ResolveAIO:

- [ResolveAIODemoEffect.cpp](/Volumes/Transcend/resolve plugin aio/resolve-aio/src/ofx/effects/ResolveAIODemoEffect.cpp)
- [ResolveAIODemoEffect.h](/Volumes/Transcend/resolve plugin aio/resolve-aio/src/ofx/effects/ResolveAIODemoEffect.h)

Build entry points live in:

- [src/ofx/CMakeLists.txt](/Volumes/Transcend/resolve plugin aio/resolve-aio/src/ofx/CMakeLists.txt)
- [src/ofx/plugin_host.cpp](/Volumes/Transcend/resolve plugin aio/resolve-aio/src/ofx/plugin_host.cpp)

It is a minimal filter plugin scaffold intended to be built against an installed OpenFX SDK. The render path currently returns the host default response; add actual pixel processing here when implementing the first production effect.
