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

   🔧  Installed CLIs Agents - Ready to Use:
      • Claude CLI    → claude
      • OpenCode CLI  → opencode

  🤖 ═══════════════════════════════════════════════════════════ 🤖

EOF