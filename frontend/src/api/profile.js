import axiosClient from "./axiosClient";
import toFormData from "./formData";

/** Own profile view/update for whichever role is logged in. */
const profileAPI = {
  get() {
    return axiosClient.get("/profile/");
  },
  /** Multipart (profile_pic); password only sent when set. */
  update(data) {
    return axiosClient.put("/profile/", toFormData(data), {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export default profileAPI;
