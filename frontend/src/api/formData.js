/**
 * Convert a plain object to FormData for multipart endpoints (profile_pic
 * uploads). Arrays are appended once per item (Django's getlist pattern);
 * null/undefined values are skipped so optional files don't clobber
 * existing ones on edit.
 */
export default function toFormData(obj) {
  const fd = new FormData();
  Object.entries(obj).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (Array.isArray(value)) {
      value.forEach((v) => fd.append(key, v));
    } else {
      fd.append(key, value);
    }
  });
  return fd;
}
