import subprocess, sys, pkg_resources

def install(name):
    subprocess.check_call([sys.executable, "-m", "pip", "install", name])

for pkg in ("sshpass", "expect"):
    try:
        pkg_resources.get_distribution(pkg)
    except pkg_resources.DistributionNotFound:
        pass   # apt packages; skip pip install
