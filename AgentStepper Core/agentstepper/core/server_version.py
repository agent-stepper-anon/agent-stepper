
DEBUGGER_SERVER_VERSION = 'v1.0.0-beta.pre-2'
'''
Current release version of the debugger server.
'''

import re
from typing import Tuple, Optional

def parse_version(version: str) -> Tuple[int, int, int, Optional[str], Optional[int]]:
    """
    Parse a version string into its components.
    Returns: (major, minor, patch, label, pre_version)
    """
    # Regex pattern for version string
    pattern = r'^v(\d+)\.(\d+)\.(\d+)(?:-(beta|alpha)(?:\.pre-(\d+))?)?$'
    match = re.match(pattern, version)
    
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    label = match.group(4)  # beta/alpha or None
    pre_version = int(match.group(5)) if match.group(5) else None
    
    return major, minor, patch, label, pre_version

def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings according to semantic versioning.
    Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    
    # Compare major, minor, patch
    for i in range(3):
        if v1[i] < v2[i]:
            return -1
        elif v1[i] > v2[i]:
            return 1
    
    # If versions are equal up to patch, compare labels
    label1, pre1 = v1[3], v1[4]
    label2, pre2 = v2[3], v2[4]
    
    # No label is greater than any label
    if label1 is None and label2 is not None:
        return 1
    elif label1 is not None and label2 is None:
        return -1
    elif label1 is None and label2 is None:
        return 0
    
    # Compare labels (alpha < beta)
    if label1 == 'alpha' and label2 == 'beta':
        return -1
    elif label1 == 'beta' and label2 == 'alpha':
        return 1
    
    # Same label, compare pre-version if exists
    if pre1 is None and pre2 is not None:
        return 1
    elif pre1 is not None and pre2 is None:
        return -1
    elif pre1 is None and pre2 is None:
        return 0
    
    # Compare pre-version numbers
    return 1 if pre1 > pre2 else -1 if pre1 < pre2 else 0

def is_compatible(required: str, provided: str) -> bool:
    """
    Check if provided version is compatible with required version.
    Rules:
    1. Major and minor must be greater or equal
    2. Patch can deviate
    3. If M.m.p are equal, alpha is not compatible with beta
    4. If label is same, pre-version must be greater or equal
    """
    req = parse_version(required)
    prov = parse_version(provided)
    
    # Rule 1: Major and minor must be greater or equal
    if prov[0] < req[0] or prov[1] < req[1]:
        return False
    
    # If major, minor, patch are equal, check labels
    if req[0] == prov[0] and req[1] == prov[1] and req[2] == prov[2]:
        req_label, req_pre = req[3], req[4]
        prov_label, prov_pre = prov[3], prov[4]
        
        # If no labels, compatible
        if req_label is None and prov_label is None:
            return True
            
        # Rule 3: alpha not compatible with beta
        if req_label != prov_label:
            return False
            
        # Rule 4: Same label, pre-version must be greater or equal
        if req_pre is not None and prov_pre is not None:
            return prov_pre >= req_pre
            
        # If required has pre-version but provided doesn't, not compatible
        if req_pre is not None and prov_pre is None:
            return False
            
        # If provided has pre-version but required doesn't, compatible
        if req_pre is None and prov_pre is not None:
            return True
            
        # Same label, no pre-versions
        return True
    
    # Rule 2: Patch can deviate if major/minor compatible
    return True

# Test cases for version compatibility
""" print(f"Is v1.0.0 and v1.0.0 compatible? {is_compatible('v1.0.0', 'v1.0.0')}")
print(f"Is v1.0.0 and v1.0.1 compatible? {is_compatible('v1.0.0', 'v1.0.1')}")
print(f"Is v1.0.1 and v1.0.0 compatible? {is_compatible('v1.0.1', 'v1.0.0')}")
print(f"Is v1.0.0 and v1.1.0 compatible? {is_compatible('v1.0.0', 'v1.1.0')}")
print(f"Is v1.1.0 and v1.0.0 compatible? {is_compatible('v1.1.0', 'v1.0.0')}")
print(f"Is v1.0.0 and v2.0.0 compatible? {is_compatible('v1.0.0', 'v2.0.0')}")
print(f"Is v2.0.0 and v1.0.0 compatible? {is_compatible('v2.0.0', 'v1.0.0')}")
print(f"Is v1.0.0-alpha and v1.0.0-beta compatible? {is_compatible('v1.0.0-alpha', 'v1.0.0-beta')}")
print(f"Is v1.0.0-beta and v1.0.0-alpha compatible? {is_compatible('v1.0.0-beta', 'v1.0.0-alpha')}")
print(f"Is v1.0.0-alpha and v1.0.0-alpha compatible? {is_compatible('v1.0.0-alpha', 'v1.0.0-alpha')}")
print(f"Is v1.0.0-alpha.pre-1 and v1.0.0-alpha.pre-2 compatible? {is_compatible('v1.0.0-alpha.pre-1', 'v1.0.0-alpha.pre-2')}")
print(f"Is v1.0.0-alpha.pre-2 and v1.0.0-alpha.pre-1 compatible? {is_compatible('v1.0.0-alpha.pre-2', 'v1.0.0-alpha.pre-1')}")
print(f"Is v1.0.0-alpha and v1.0.0-alpha.pre-1 compatible? {is_compatible('v1.0.0-alpha', 'v1.0.0-alpha.pre-1')}")
print(f"Is v1.0.0-alpha.pre-1 and v1.0.0-alpha compatible? {is_compatible('v1.0.0-alpha.pre-1', 'v1.0.0-alpha')}")
print(f"Is v1.0.0 and v1.0.0-alpha compatible? {is_compatible('v1.0.0', 'v1.0.0-alpha')}")
print(f"Is v1.0.0-alpha and v1.0.0 compatible? {is_compatible('v1.0.0-alpha', 'v1.0.0')}") """