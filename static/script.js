// ===============================
// SAFE HELPER FUNCTIONS (FLASK FRIENDLY)
// ===============================

// Placeholder API functions (replace with Flask endpoints later)
async function getAttendanceRecords(workerId = null) {
    // TODO: Replace with real API call
    return [];
}

async function getSalaryRecords() {
    // TODO: Replace with real API call
    return [];
}

// ===============================
// ATTENDANCE CALCULATION
// ===============================
async function calculateTotalDaysPresent(workerId) {
    const attendanceRecords = await getAttendanceRecords(workerId);

    let totalDaysPresent = 0;

    attendanceRecords.forEach(record => {
        if (record.status && record.status.toLowerCase() === 'present') {
            totalDaysPresent++;
        }
    });

    return totalDaysPresent;
}

// ===============================
// SALARY CALCULATION
// ===============================
async function calculateSalary(workerId, dailyRate) {
    const totalDaysPresent = await calculateTotalDaysPresent(workerId);
    return totalDaysPresent * dailyRate;
}

// ===============================
// MOVE TO ATTENDANCE HISTORY
// ===============================
document.addEventListener("DOMContentLoaded", function () {
    const attendanceBtn = document.getElementById('move-to-attendance-history');

    if (attendanceBtn) {
        attendanceBtn.addEventListener('click', async () => {
            try {
                const currentMonth = new Date().getMonth() + 1;
                const currentYear = new Date().getFullYear();

                // TODO: Replace with Flask route call
                console.log("Moving attendance:", currentMonth, currentYear);

            } catch (error) {
                console.error("Attendance history error:", error);
            }
        });
    }

    // ===============================
    // MOVE TO SALARY HISTORY
    // ===============================
    const salaryBtn = document.getElementById('move-to-salary-history');

    if (salaryBtn) {
        salaryBtn.addEventListener('click', async () => {
            try {
                const currentMonth = new Date().getMonth() + 1;
                const currentYear = new Date().getFullYear();

                console.log("Moving salary:", currentMonth, currentYear);

            } catch (error) {
                console.error("Salary history error:", error);
            }
        });
    }
});

// ===============================
// FILTER ATTENDANCE
// ===============================
async function filterAttendanceRecords(name = "", month = "", workerId = "") {
    const attendanceRecords = await getAttendanceRecords();

    return attendanceRecords.filter(record => {
        if (name && record.workerName !== name) return false;
        if (month && record.month !== month) return false;
        if (workerId && record.workerId !== workerId) return false;
        return true;
    });
}

// ===============================
// FILTER SALARY
// ===============================
async function filterSalaryRecords(month = "") {
    const salaryRecords = await getSalaryRecords();

    return salaryRecords.filter(record => {
        if (month && record.month !== month) return false;
        return true;
    });
}