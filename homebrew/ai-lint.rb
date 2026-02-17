class AiLint < Formula
  include Language::Python::Virtualenv

  desc "Check AI coding session compliance against user-defined policies"
  homepage "https://github.com/Telomelonia/ai-lint"
  url "https://github.com/Telomelonia/ai-lint/archive/refs/tags/v0.3.8.tar.gz"
  sha256 "e2b32c31f37bcb70ea66a3c4c37af3cf0c4e5489e5cb1db6422f3688380e1aec"
  license "MIT"

  depends_on "python@3.12"

  resource "click" do
    url "https://files.pythonhosted.org/packages/96/d3/f04c7bfcf5c1862a2a5b845c6b2b360488cf47af55dfa79c98f6a6bf98b5/click-8.1.7.tar.gz"
    sha256 "ca9853ad459e787e2192211578cc907e7594e294c7ccc834310722b41b9ca6de"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "ai-lint", shell_output("#{bin}/ai-lint --help")
  end
end
