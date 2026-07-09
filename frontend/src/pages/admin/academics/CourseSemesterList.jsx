import { Link, useParams } from "react-router-dom";
import { subjectAPI } from "../../../api/academics";
import { BackButton, ListCard } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/**
 * Manage Subjects — semester tiles for one course
 * (course_semester_list.html; narrower col-md-3 tiles than the student flow).
 */
function CourseSemesterList() {
  const { courseId } = useParams();
  const { data } = useApi(() => subjectAPI.manageSemesters(courseId), [courseId]);

  const course = data?.course;
  const title = course
    ? `Manage Subjects - ${course.short_name} (Select Semester)`
    : "Manage Subjects";
  usePageHeader({ title, breadcrumb: [{ text: "Manage Subjects" }] });

  return (
    <ListCard
      title={title}
      action={<BackButton to="/course/manage/">Back to Courses</BackButton>}
    >
      {data && !data.semester_data?.length ? (
        <>
          <p className="text-muted">
            No semesters have been configured for this course.
          </p>
          <Link to={`/course/edit/${courseId}`} className="btn btn-primary">
            Set Number of Semesters
          </Link>
        </>
      ) : (
        <>
          <p className="text-muted">
            Select a semester to view and manage its subjects.
          </p>
          <div className="row">
            {data?.semester_data?.map((item) => (
              <div className="col-md-3 col-sm-4 col-6 mb-4 d-flex" key={item.number}>
                <Link
                  to={`/subject/manage/course/${courseId}/semester/${item.number}/`}
                  className="text-decoration-none w-100"
                >
                  <div className="card card-outline card-primary h-100 mb-0 shadow-sm">
                    <div
                      className="card-body d-flex justify-content-between align-items-center"
                      style={{ padding: "1.25rem 1.5rem" }}
                    >
                      <span className="font-weight-bold" style={{ fontSize: "1.05rem" }}>
                        Semester {item.number}
                      </span>
                      <span
                        className="badge badge-info badge-pill"
                        style={{ padding: "0.5em 0.85em", fontSize: "0.85rem" }}
                      >
                        {item.subject_count}
                      </span>
                    </div>
                  </div>
                </Link>
              </div>
            ))}
          </div>
        </>
      )}
    </ListCard>
  );
}

export default CourseSemesterList;
