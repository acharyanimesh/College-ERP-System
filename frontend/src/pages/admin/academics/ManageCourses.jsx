import { Link } from "react-router-dom";
import { courseAPI } from "../../../api/academics";
import { ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/** Manage Courses table (hod_template/manage_course.html). */
function ManageCourses() {
  usePageHeader({
    title: "Manage Courses",
    breadcrumb: [{ text: "Manage Courses" }],
  });
  const { addMessage } = useMessages();
  const { data: courses, reload } = useApi(() => courseAPI.getAll());

  const remove = async (course) => {
    if (!window.confirm("Are you sure you want to delete this course ?")) return;
    try {
      await courseAPI.delete(course.id);
      addMessage("Course deleted successfully!", "success");
      reload();
    } catch {
      addMessage("Sorry, some students are assigned to this course already. Kindly change the affected student course and try again", "danger");
    }
  };

  return (
    <ListCard title="Manage Courses">
      <table className="table table-bordered table-hover">
        <thead className="thead-dark">
          <tr>
            <th>#</th>
            <th>Course</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {courses?.map((course, i) => (
            <tr key={course.id}>
              <td>{i + 1}</td>
              <td>
                <Link
                  to={`/subject/manage/course/${course.id}/`}
                  className="text-decoration-none"
                  style={{ color: "inherit" }}
                  title="View & manage subjects for this course"
                >
                  {course.name_with_abbr || course.name}
                </Link>
              </td>
              <td className="text-nowrap">
                <Link to={`/course/edit/${course.id}`} className="btn btn-sm btn-info" title="Edit">
                  <i className="fas fa-edit"></i>
                </Link>{" "}
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  title="Delete"
                  onClick={() => remove(course)}
                >
                  <i className="fas fa-trash"></i>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </ListCard>
  );
}

export default ManageCourses;
