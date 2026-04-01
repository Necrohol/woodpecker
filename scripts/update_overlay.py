import os, requests

REPO_ROOT = os.getcwd()
API_URL = "https://github.com"
MAX_VERSIONS = 4
PKGS = ["server", "agent", "cli"]

def setup_accounts():
    """Creates acct-group and acct-user if they don't exist."""
    for cat in ["acct-group", "acct-user"]:
        path = os.path.join(REPO_ROOT, cat, "woodpecker")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            content = "EAPI=8\ninherit " + cat.replace("-", "_") + "\n"
            content += "ACCT_USER_ID=404\nACCT_USER_GROUPS=( woodpecker )\n" if "user" in cat else "ACCT_GROUP_ID=404\n"
            with open(os.path.join(path, "woodpecker-0.ebuild"), "w") as f:
                f.write(content)

def update_binaries():
    releases = requests.get(API_URL).json()
    # Gentoo versioning: 3.0.0-rc1 -> 3.0.0_rc1
    versions = [(r['tag_name'].lstrip('v'), r['tag_name'].lstrip('v').replace('-', '_')) for r in releases][:MAX_VERSIONS]

    for suffix in PKGS:
        pkg_name = f"woodpecker-{suffix}"
        path = os.path.join(REPO_ROOT, "dev-util", pkg_name)
        os.makedirs(path, exist_ok=True)
        
        kept_ebuilds = []
        for raw_v, gentoo_v in versions:
            ebuild_name = f"{pkg_name}-{gentoo_v}.ebuild"
            kept_ebuilds.append(ebuild_name)
            
            with open(os.path.join(path, ebuild_name), "w") as f:
                f.write(f'''EAPI=8
DESCRIPTION="Woodpecker CI {suffix} (binary)"
HOMEPAGE="https://woodpecker-ci.org"
SRC_URI="https://github.com{raw_v}/woodpecker-{suffix}_linux_amd64.tar.gz"
S="${{WORKDIR}}"
LICENSE="Apache-2.0"
SLOT="0"
KEYWORDS="~amd64"
RESTRICT="strip"
RDEPEND="acct-user/woodpecker"
src_install() {{ dobin woodpecker-{suffix}; }}
''')
        
        # Prune
        for f in os.listdir(path):
            if f.endswith(".ebuild") and f not in kept_ebuilds:
                os.remove(os.path.join(path, f))

if __name__ == "__main__":
    setup_accounts()
    update_binaries()
