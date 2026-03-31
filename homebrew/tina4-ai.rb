class Tina4Ai < Formula
  include Language::Python::Virtualenv

  desc "AI tools for the Tina4 family — includes mdview Markdown viewer"
  homepage "https://github.com/tina4stack/tina4-ai"
  url "https://files.pythonhosted.org/packages/source/t/tina4-ai/tina4_ai-0.1.0.tar.gz"
  sha256 "PLACEHOLDER"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "mdview", shell_output("#{bin}/mdview --help 2>&1", 2)
  end
end
