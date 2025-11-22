from __future__ import annotations

import patch_ng as patch
from pathlib import Path
from io import BytesIO

from langchain.tools import tool

from .safety import ensure_path_allowed


@tool("apply_patch")
def apply_patch(
    target_file: str,
    diff_content: str,
) -> dict:
    """
    Apply a unified diff to a file.
    
    Args:
        target_file: The file to apply the patch to.
        diff_content: The unified diff content.
    """
    resolved = ensure_path_allowed(target_file)
    path_obj = Path(resolved)
    
    if not path_obj.exists():
        return {"error": True, "message": f"Target file '{target_file}' does not exist."}
    
    try:
        # Create a patch set from the diff content
        # We need to make sure the diff content is bytes for patch_ng
        diff_bytes = diff_content.encode('utf-8')
        pset = patch.fromstring(diff_bytes)
        
        if not pset:
            return {"error": True, "message": "Could not parse diff content."}
        
        # We assume the diff is for the target file. 
        # patch_ng usually expects headers in the diff to match files, 
        # but we can try to force apply to the specific file if we read it first.
        
        # Actually, patch_ng.apply works on files or streams.
        # Let's try applying to the file directly.
        
        # Since the diff might have headers that don't match the absolute path,
        # we might need to be careful.
        
        # Strategy: Read file, apply patch in memory, write back.
        src_content = path_obj.read_bytes()
        
        # We need to pass a stream to apply
        # But patch_ng is a bit complex.
        # Simpler approach: use the 'patch' command if available? 
        # No, we want pure python if possible for portability, but patch_ng is a library.
        
        # patch_ng PatchSet is iterable directly in newer versions or via .items
        # Let's check how to access items. It seems it behaves like a list in some versions but maybe not this one?
        # Actually, looking at patch_ng source, PatchSet inherits from list in some versions, but let's be safe.
        
        if not pset.items:
             return {"error": True, "message": "No patches found in diff."}

        p = pset.items[0]
        
        # patch_ng doesn't have a simple "apply to string" method that is robust without headers matching.
        # However, we can try.
        
        # If the user provides a diff, it usually has:
        # --- a/file
        # +++ b/file
        # @@ ... @@
        
        # If we just want to apply the hunks to the provided target_file:
        # We need to pass the root directory.
        
        # Hack: modify the patch object to point to the target file name relative to root
        p.source = path_obj.name.encode('utf-8')
        p.target = path_obj.name.encode('utf-8')
        
        # Now apply relative to parent
        success = pset.apply(root=path_obj.parent)
        
        if success:
            return {
                "error": False,
                "path": str(resolved),
                "message": "Patch applied successfully."
            }
        else:
            return {
                "error": True,
                "message": "Failed to apply patch. Hunks might not match."
            }

    except Exception as e:
        # Fallback: try using system patch command if python patch fails?
        # For now, return error.
        return {"error": True, "message": f"Error applying patch: {e}"}
