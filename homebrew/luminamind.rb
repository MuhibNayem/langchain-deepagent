class Luminamind < Formula
  desc "Autonomous agent platform with swarm intelligence"
  homepage "https://github.com/amnayem/luminamind"
  url "https://github.com/amnayem/luminamind.git"
  version "1.0.0"
  sha256 "abc123..."  # Would be computed from actual release

  depends_on "docker"

  def install
    # Create convenience script
    bin.write_script "luminamind.sh", <<~EOS
      #!/bin/bash
      exec docker run --rm \\
        -v ~/.luminamind:/config \\
        ghcr.io/amnayem/luminamind:latest \\
        "$@"
    EOS
  end

  test do
    system "docker", "run", "--rm", "ghcr.io/amnayem/luminamind:latest", "echo", "LuminaMind"
  end
end
