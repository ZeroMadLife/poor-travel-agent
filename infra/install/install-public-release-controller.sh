#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "must run as root" >&2
  exit 2
fi

repo_root=${1:-/opt/sage/app}
source_script="$repo_root/scripts/public_releasectl.py"
package_script="$repo_root/scripts/public_packagectl.py"
source_sudoers="$repo_root/infra/sudoers/sage-public-release"
public_agent_env=/etc/sage/public-agent.env
package_registry=/var/lib/sage-public-release/packages

test -f "$source_script"
test -f "$package_script"
test -f "$source_sudoers"
python3 -m py_compile "$source_script"
python3 -m py_compile "$package_script"
visudo -cf "$source_sudoers"
test -f "$public_agent_env"
test "$(stat -c '%U:%G %a' "$public_agent_env")" = "root:root 600"

install -d -o root -g root -m 0700 /var/lib/sage-public-release
install -d -o root -g root -m 0755 "$package_registry"
install -o root -g root -m 0755 "$source_script" /usr/local/sbin/sage-public-releasectl
install -o root -g root -m 0755 "$package_script" /usr/local/sbin/sage-public-packagectl
install -o root -g root -m 0440 "$source_sudoers" /etc/sudoers.d/sage-public-release
visudo -cf /etc/sudoers.d/sage-public-release

SAGE_PUBLIC_APP_ROOT="$repo_root" python3 "$package_script" \
  --registry-root "$package_registry" \
  --bootstrap-package "$repo_root/data/public/sage-public-v1.json" >/dev/null

printf '%s\n' '{"action":"status"}' | sudo -u sage-deploy sudo -n /usr/local/sbin/sage-public-releasectl >/dev/null
printf '%s\n' '{"action":"status"}' | sudo -u sage-deploy sudo -n /usr/local/sbin/sage-public-packagectl >/dev/null
echo "public release controller installed"
