import { useState } from "react";
import resultAPI from "../../api/results";
import { ListCard } from "../../components/ListCard";
import useApi from "../../hooks/useApi";
import { usePageHeader } from "../../layouts/Layout";

/**
 * Student "View Result" (student_template/student_view_result.html):
 * semester selector + subject/test/exam/total table.
 */
function StudentViewResult() {
  usePageHeader({
    title: "View Result",
    breadcrumb: [{ text: "View Result" }],
  });
  const [semester, setSemester] = useState("");

  // API mirrors the view context: { semesters, selected, rows:
  //   [{ subject_name, result: {test, exam}|null }] }
  const { data } = useApi(
    () => resultAPI.getMine(semester ? { semester } : {}),
    [semester]
  );

  const selected = semester || (data ? String(data.selected) : "");

  return (
    <ListCard dark title="View Result">
      {data && !data.semesters?.length ? (
        <p className="text-muted mb-0">
          No subjects are assigned to your course yet.
        </p>
      ) : (
        <>
          <form className="form-inline mb-3">
            <label htmlFor="semester" className="mr-2 me-2">
              Semester
            </label>
            <select
              id="semester"
              className="form-control"
              value={selected}
              onChange={(e) => setSemester(e.target.value)}
            >
              {data?.semesters?.map((sem) => (
                <option key={sem} value={sem}>
                  Semester {sem}
                </option>
              ))}
            </select>
          </form>

          <div className="table p-0" style={{ overflowX: "auto", overflowY: "auto", maxHeight: 600 }}>
            <table className="table table-bordered" style={{ minWidth: 600 }}>
              <thead className="thead-dark">
                <tr>
                  <th>ID</th>
                  <th>Subject</th>
                  <th>Test</th>
                  <th>Exam</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {data?.rows?.length ? (
                  data.rows.map((row, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{row.subject_name}</td>
                      {row.result ? (
                        <>
                          <td>{row.result.test}</td>
                          <td>{row.result.exam}</td>
                          <td>{Number(row.result.test) + Number(row.result.exam)}</td>
                        </>
                      ) : (
                        <td colSpan={3} className="text-muted">
                          Not published yet
                        </td>
                      )}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="text-center">
                      No subjects found for this semester.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </ListCard>
  );
}

export default StudentViewResult;
