#!/bin/bash

DOTNET_VERSION=$(command -v dotnet >/dev/null && dotnet --version || echo "n/a")

cat << EOF

  🤖 ═══════════════════════════════════════════════════════════ 🤖
  
   █████╗ ██╗    ██████╗ ██╗   ██╗██████╗ ██████╗ ██╗   ██╗
  ██╔══██╗██║    ██╔══██╗██║   ██║██╔══██╗██╔══██╗╚██╗ ██╔╝
  ███████║██║    ██████╔╝██║   ██║██║  ██║██║  ██║ ╚████╔╝
  ██╔══██║██║    ██╔══██╗██║   ██║██║  ██║██║  ██║  ╚██╔╝
  ██║  ██║██║    ██████╔╝╚██████╔╝██████╔╝██████╔╝   ██║
  ╚═╝  ╚═╝╚═╝    ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝    ╚═╝
  
   AI Agent Development Container
  
   📦  Installed SDKs: .NET $DOTNET_VERSION

   🔧  Installed CLIs - Ready to Use:
      • Claude CLI    → claude
      • GitHub CLI    → gh
      • OpenCode CLI  → opencode
      • Pi CLI        → pi

  🤖 ═══════════════════════════════════════════════════════════ 🤖

EOF
