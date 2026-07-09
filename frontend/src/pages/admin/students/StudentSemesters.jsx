import { Link, useParams } from "react-router-dom";
import studentAPI from "../../../api/students";
import { BackButton, ListCard, Tile, TileGrid } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader, useMessages } from "../../../layouts/Layout";

/**
 * Manage Students — semester tiles with cascading promote / pass-out
 * actions (student_semester_list.html + promote_class).
 */
function StudentSemesters() {
  const { courseId } = useParams();
  const { addMessage } = useMessages();
  const { data, reload } = useApi(
    () => studentAPI.manageSemesters(courseId),
    [courseId]
  );

  const course = data?.course;
  const totalSemesters = data?.total_semesters || 0;
  const title = course
    ? `Manage Students - ${course.short_name} (Select Semester)`
    : "Manage Students";
  usePageHeader({ title, breadcrumb: [{ text: "Manage Students" }] });

  const promote = async (semester, count) => {
    const isFinal = semester >= totalSemesters;
    const question = isFinal
      ? `Mark all ${count} final-semester student(s) of Semester ${semester} (both shifts) as PASSED OUT? They move to Passed Out records and leave the active student body.`
      : `Promote Semester ${semester} AND every higher semester up by one (both shifts)? Final-semester students will be marked as passed out. This cannot be undone.`;
    if (!window.confirm(question)) return;
    try {
      const res = await studentAPI.promote(courseId, semester);
      addMessage(res?.detail || "Promotion applied.", "success");
      reload();
    } catch {
      addMessage("Could not promote the class.", "danger");
    }
  };

  return (
    <ListCard
      title={title}
      action={<BackButton to="/student/manage/">Back to Courses</BackButton>}
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
            Select a semester to view its students. Promoting a semester moves
            it <strong>and every higher semester</strong> up by one (both
            shifts), so batches never mix. Final-semester students are marked
            as <strong>passed out</strong>.
          </p>
          <div className="text-right text-end mb-3">
            <Link
              to="/student/passed-out/"
              className="btn btn-outline-secondary btn-sm"
            >
              <i className="fas fa-user-graduate"></i> Passed Out Students
            </Link>
          </div>
          <TileGrid>
            {data?.semester_data?.map((item) => (
              <Tile
                key={item.number}
                to={`/student/manage/course/${courseId}/semester/${item.number}/`}
                label={`Semester ${item.number}`}
                badge={item.student_count}
                footer={
                  !item.student_count ? (
                    <span style={{ fontSize: "0.8rem" }}>
                      Semester currently not active
                    </span>
                  ) : item.number >= totalSemesters ? (
                    <button
                      type="button"
                      className="btn btn-outline-primary btn-sm"
                      onClick={() => promote(item.number, item.student_count)}
                    >
                      <i className="fas fa-user-graduate"></i> Pass out Sem{" "}
                      {item.number}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-outline-success btn-sm"
                      onClick={() => promote(item.number, item.student_count)}
                    >
                      <i className="fas fa-arrow-up"></i> Promote Sem{" "}
                      {item.number} &amp; above
                    </button>
                  )
                }
              />
            ))}
          </TileGrid>
        </>
      )}
    </ListCard>
  );
}

export default StudentSemesters;
