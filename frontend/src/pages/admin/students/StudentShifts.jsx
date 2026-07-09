import { useParams } from "react-router-dom";
import studentAPI from "../../../api/students";
import { BackButton, ListCard, Tile, TileGrid } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/** Manage Students — shift tiles (student_shift_list.html). */
function StudentShifts() {
  const { courseId, semester } = useParams();
  const { data } = useApi(
    () => studentAPI.manageShifts(courseId, semester),
    [courseId, semester]
  );

  const course = data?.course;
  const title = course
    ? `Manage Students - ${course.short_name} - Semester ${semester} (Select Shift)`
    : "Manage Students";
  usePageHeader({ title, breadcrumb: [{ text: "Manage Students" }] });

  return (
    <ListCard
      title={title}
      action={
        <BackButton to={`/student/manage/course/${courseId}/`}>
          Back to Semesters
        </BackButton>
      }
    >
      <p className="text-muted">
        Select a shift to view students of{" "}
        <strong title={course?.name}>{course?.short_name}</strong> &mdash;
        Semester {semester}. Promotion is done per semester (for the whole
        course) from the previous screen.
      </p>
      <TileGrid>
        {data?.shift_data?.map((item) => (
          <Tile
            key={item.value}
            to={`/student/manage/course/${courseId}/semester/${semester}/shift/${item.value}/`}
            label={item.label}
            badge={item.student_count}
            footer={
              !item.student_count ? (
                <span style={{ fontSize: "0.8rem" }}>No students in this shift</span>
              ) : undefined
            }
          />
        ))}
      </TileGrid>
    </ListCard>
  );
}

export default StudentShifts;
