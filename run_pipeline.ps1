param(
    [string]$Mode = "BALANCED",
    [string]$ModelName,
    [string]$VideoPath
)

if (-not $ModelName -or -not $VideoPath) {
    Write-Host "ModelName and VideoPath are required."
    exit 1
}

# ======================================================
# CONFIGURATION
# ======================================================

$BasePath = Join-Path $PSScriptRoot "Models"
$ModelPath = Join-Path $BasePath $ModelName
$FramesPath = Join-Path $ModelPath "frames"
$GeometryPath = Join-Path $ModelPath "geometry"
$OutputPath = Join-Path $ModelPath "output"

Write-Host "================================="
Write-Host "HYBRID AR PIPELINE"
Write-Host "Model: $ModelName"
Write-Host "Mode: $Mode"
Write-Host "================================="

# ======================================================
# DIRECTORY SETUP
# ======================================================

New-Item -ItemType Directory -Path $ModelPath -Force | Out-Null
Copy-Item -Path $VideoPath -Destination (Join-Path $ModelPath "input_video.mp4") -Force

Remove-Item -Recurse -Force $FramesPath -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $GeometryPath -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $OutputPath -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path $FramesPath -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $GeometryPath "sparse") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $GeometryPath "dense") -Force | Out-Null
New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null

# ======================================================
# PERFORMANCE PROFILE
# ======================================================

switch ($Mode) {
    "FAST"     { $TargetFrames = 40 }
    "BALANCED" { $TargetFrames = 50 }
    "HQ"       { $TargetFrames = 65 }
    default    { $TargetFrames = 50 }
}

# ======================================================
# FRAME EXTRACTION
# ======================================================

Write-Host "[STAGE] FRAME_EXTRACTION"

& python "scripts\extract_frames.py" `
    $TargetFrames `
    (Join-Path $ModelPath "input_video.mp4") `
    $FramesPath

if ($LASTEXITCODE -ne 0) { exit 1 }

# ======================================================
# FEATURE EXTRACTION
# ======================================================

Write-Host "[STAGE] FEATURE_EXTRACTION"

& colmap feature_extractor `
    --database_path (Join-Path $GeometryPath "database.db") `
    --image_path $FramesPath `
    --ImageReader.camera_model SIMPLE_RADIAL

if ($LASTEXITCODE -ne 0) { exit 1 }

# ======================================================
# MATCHING
# ======================================================

Write-Host "[STAGE] MATCHING"

& colmap exhaustive_matcher `
    --database_path (Join-Path $GeometryPath "database.db")

if ($LASTEXITCODE -ne 0) { exit 1 }

# ======================================================
# SPARSE
# ======================================================

Write-Host "[STAGE] SPARSE"

& colmap mapper `
    --database_path (Join-Path $GeometryPath "database.db") `
    --image_path $FramesPath `
    --output_path (Join-Path $GeometryPath "sparse")

if (!(Test-Path (Join-Path $GeometryPath "sparse\0"))) {
    Write-Host "Sparse reconstruction failed."
    exit 1
}

# Export sparse PLY for viewer
& colmap model_converter `
    --input_path (Join-Path $GeometryPath "sparse\0") `
    --output_path (Join-Path $GeometryPath "sparse\0\sparse.ply") `
    --output_type PLY

# ======================================================
# UNDISTORT
# ======================================================

Write-Host "[STAGE] UNDISTORT"

& colmap image_undistorter `
    --image_path $FramesPath `
    --input_path (Join-Path $GeometryPath "sparse\0") `
    --output_path (Join-Path $GeometryPath "dense") `
    --output_type COLMAP

if ($LASTEXITCODE -ne 0) { exit 1 }

# ======================================================
# DENSE
# ======================================================

Write-Host "[STAGE] DENSE"

& colmap patch_match_stereo `
    --workspace_path (Join-Path $GeometryPath "dense") `
    --workspace_format COLMAP `
    --PatchMatchStereo.geom_consistency true

if ($LASTEXITCODE -ne 0) { exit 1 }

# ======================================================
# FUSION
# ======================================================

Write-Host "[STAGE] FUSION"

& colmap stereo_fusion `
    --workspace_path (Join-Path $GeometryPath "dense") `
    --workspace_format COLMAP `
    --input_type geometric `
    --output_path (Join-Path $GeometryPath "dense\fused.ply")

if (!(Test-Path (Join-Path $GeometryPath "dense\fused.ply"))) {
    Write-Host "Fusion failed."
    exit 1
}

# ======================================================
# MESH (POISSON ONLY)
# ======================================================

Write-Host "[STAGE] MESH"

& colmap poisson_mesher `
    --input_path (Join-Path $GeometryPath "dense\fused.ply") `
    --output_path (Join-Path $OutputPath "mesh.ply")

if (!(Test-Path (Join-Path $OutputPath "mesh.ply"))) {
    Write-Host "Mesh generation failed."
    exit 1
}

# ======================================================
# GLB
# ======================================================

Write-Host "[STAGE] GLB"

& python "scripts\export_glb.py" `
    (Join-Path $OutputPath "mesh.ply") `
    (Join-Path $OutputPath "model.glb")

if (!(Test-Path (Join-Path $OutputPath "model.glb"))) {
    Write-Host "GLB export failed."
    exit 1
}

Write-Host "================================="
Write-Host "PIPELINE COMPLETE"
Write-Host "Model saved at: $OutputPath"
Write-Host "================================="