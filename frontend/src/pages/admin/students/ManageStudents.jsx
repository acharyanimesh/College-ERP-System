import studentAPI from "../../../api/students";
import { ListCard, Tile, TileGrid } from "../../../components/ListCard";
import useApi from "../../../hooks/useApi";
import { usePageHeader } from "../../../layouts/Layout";

/** Manage Students — course tiles (hod_template/manage_student.html). */
function ManageStudents() {
  usePageHeader({
    title: "Manage Students - Select Course",
    breadcrumb: [{ text: "Manage Students" }],
  });
  const { data: courseData } = useApi(() => studentAPI.manageCourses());

  return (
    <ListCard title="Manage Students - Select Course">
      <p className="text-muted">Select a course to view its students.</p>
      <TileGrid>
        {courseData?.length ? (
          courseData.map((item) => (
            <Tile
              key={item.course.id}
              to={`/student/manage/course/${item.course.id}/`}
              label={item.course.short_name}
              title={item.course.name}
              badge={item.student_count}
            />
          ))
        ) : (
          <div className="col-12">
            <p>No courses available.</p>
          </div>
        )}
      </TileGrid>
    </ListCard>
  );
}

export default ManageStudents;
