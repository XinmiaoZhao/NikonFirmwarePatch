// swift-tools-version: 5.10
// Z8 Patch Builder: macOS front end for patch.py / verify.py. Build the app bundle with
// scripts/build_app.py; `swift build` alone produces only the executable (see README.md).
import PackageDescription

let package = Package(
    name: "Z8PatchBuilder",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(name: "Z8PatchBuilder", path: "Sources/Z8PatchBuilder"),
        .testTarget(name: "Z8PatchBuilderTests", dependencies: ["Z8PatchBuilder"], path: "Tests/Z8PatchBuilderTests"),
    ]
)
