import os
import re


def expand_env_vars(content: str) -> str:
    """
    Expand placeholders of the form ${VAR:=default} or ${VAR:default} in the given string.

    Examples:
      - ${FOO} will be replaced by os.environ.get("FOO", "")
      - ${FOO:=bar} will be replaced by os.environ.get("FOO", "bar")
      - ${FOO:bar} means the same as above (Containerlab also accepts : or :=)
    """
    pattern = re.compile(r"\$\{([^:}]+):?=?([^}]*)\}")

    def replacer(match):
        var_name = match.group(1)
        default_val = match.group(2)
        # If the environment variable exists, use it; otherwise, use the default.
        return os.environ.get(var_name, default_val)

    return pattern.sub(replacer, content)
