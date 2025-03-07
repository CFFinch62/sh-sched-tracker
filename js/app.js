// Global variables
let isTestMode = false;
let testInterval;
let currentCard = null;
let colorSettings = null;
let updateInterval;

// Load or initialize color settings from localStorage
function initializeColorSettings() {
    const savedColors = localStorage.getItem('colorSettings');
    if (savedColors) {
        colorSettings = JSON.parse(savedColors);
    } else {
        colorSettings = {
            'regular': {
                'background': '#000080',
                'label': '#FFFFFF',
                'message': '#FFFF00'
            },
            'two_hour_delay': {
                'background': '#000080',
                'label': '#FFFFFF',
                'message': '#FFFF00'
            },
            'homeroom': {
                'background': '#000080',
                'label': '#FFFFFF',
                'message': '#FFFF00'
            }
        };
        localStorage.setItem('colorSettings', JSON.stringify(colorSettings));
    }
    applyColors();
}

// Get current period based on time
function getCurrentPeriod(scheduleType, currentTime) {
    const schedule = SCHEDULES.southampton_high_school[scheduleType];
    if (!schedule || !schedule.periods) return "No schedule defined";

    const periods = schedule.periods;
    const timeObj = new Date();
    const [hours, minutes] = currentTime.split(':').map(Number);
    timeObj.setHours(hours, minutes, 0);

    // Before school check (00:00 to start of schedule)
    const firstPeriod = periods.find(p => p.start);
    if (firstPeriod) {
        const firstStart = new Date();
        const [fHours, fMinutes] = firstPeriod.start.split(':').map(Number);
        firstStart.setHours(fHours, fMinutes, 0);
        if (timeObj < firstStart) return "Before School";
    }

    // After school check (14:30 to 23:59)
    const afterSchool = new Date();
    afterSchool.setHours(14, 30, 0);
    if (timeObj > afterSchool) return "After School";

    // Find Period 1
    const period1 = periods.find(p => p.name === "1");
    if (period1) {
        const period1Start = new Date();
        const [p1Hours, p1Minutes] = period1.start.split(':').map(Number);
        period1Start.setHours(p1Hours, p1Minutes, 0);
        if (timeObj < period1Start) {
            return `Period 1 starts at ${period1.start}`;
        }
    }

    // Check current period and transitions
    for (let i = 0; i < periods.length; i++) {
        const period = periods[i];
        if (!period.start || !period.end) continue;

        const startTime = new Date();
        const endTime = new Date();
        const [sHours, sMinutes] = period.start.split(':').map(Number);
        const [eHours, eMinutes] = period.end.split(':').map(Number);
        startTime.setHours(sHours, sMinutes, 0);
        endTime.setHours(eHours, eMinutes, 0);

        // During a period
        if (timeObj >= startTime && timeObj <= endTime) {
            return period.name.match(/^\d+$/) ? `Period ${period.name}` : period.name;
        }

        // Between periods
        if (i < periods.length - 1) {
            const nextPeriod = periods[i + 1];
            const nextStart = new Date();
            const [nHours, nMinutes] = nextPeriod.start.split(':').map(Number);
            nextStart.setHours(nHours, nMinutes, 0);

            if (timeObj > endTime && timeObj < nextStart) {
                const currentName = period.name.match(/^\d+$/) ? 
                    `Period ${period.name}` : period.name;
                const nextName = nextPeriod.name.match(/^\d+$/) ? 
                    `Period ${nextPeriod.name}` : nextPeriod.name;
                return `${currentName} → ${nextName}`;
            }
        }
    }

    return "Not in session";
}

// Update the display
function updateDisplay(testTime = null) {
    const now = testTime ? new Date(`2000-01-01 ${testTime}`) : new Date();
    const timeStr = now.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit'
    });

    document.getElementById('currentTime').textContent = timeStr;
    document.getElementById('regularSchedule').textContent = 
        getCurrentPeriod('regular_schedule', timeStr);
    document.getElementById('delaySchedule').textContent = 
        getCurrentPeriod('two_hour_delay', timeStr);
    document.getElementById('homeroomSchedule').textContent = 
        getCurrentPeriod('homeroom_schedule', timeStr);
}

// Color management functions
function applyColors() {
    try {
        const regularCard = document.getElementById('regularSchedule');
        const delayCard = document.getElementById('delaySchedule');
        const homeroomCard = document.getElementById('homeroomSchedule');

        if (regularCard && delayCard && homeroomCard) {
            // Regular schedule
            const regularParent = regularCard.parentElement;
            regularParent.style.backgroundColor = colorSettings.regular.background;
            regularParent.querySelector('h2').style.color = colorSettings.regular.label;
            regularCard.style.color = colorSettings.regular.message;

            // Two hour delay schedule
            const delayParent = delayCard.parentElement;
            delayParent.style.backgroundColor = colorSettings.two_hour_delay.background;
            delayParent.querySelector('h2').style.color = colorSettings.two_hour_delay.label;
            delayCard.style.color = colorSettings.two_hour_delay.message;

            // Homeroom schedule
            const homeroomParent = homeroomCard.parentElement;
            homeroomParent.style.backgroundColor = colorSettings.homeroom.background;
            homeroomParent.querySelector('h2').style.color = colorSettings.homeroom.label;
            homeroomCard.style.color = colorSettings.homeroom.message;
        }
    } catch (error) {
        console.error('Error applying colors:', error);
    }
}

function showColorDialog(scheduleType) {
    currentCard = scheduleType;
    const colors = colorSettings[scheduleType];
    
    document.getElementById('bgColorPicker').value = colors.background;
    document.getElementById('labelColorPicker').value = colors.label;
    document.getElementById('messageColorPicker').value = colors.message;
    
    document.getElementById('colorDialog').style.display = 'flex';
}

function saveColors() {
    const colors = {
        background: document.getElementById('bgColorPicker').value,
        label: document.getElementById('labelColorPicker').value,
        message: document.getElementById('messageColorPicker').value
    };
    
    colorSettings[currentCard] = colors;
    localStorage.setItem('colorSettings', JSON.stringify(colorSettings));
    
    applyColors();
    closeColorDialog();
}

function resetColors() {
    if (confirm('Reset colors to default?')) {
        colorSettings = {
            'regular': {
                'background': '#000080',
                'label': '#FFFFFF',
                'message': '#FFFF00'
            },
            'two_hour_delay': {
                'background': '#000080',
                'label': '#FFFFFF',
                'message': '#FFFF00'
            },
            'homeroom': {
                'background': '#000080',
                'label': '#FFFFFF',
                'message': '#FFFF00'
            }
        };
        
        localStorage.setItem('colorSettings', JSON.stringify(colorSettings));
        
        if (currentCard) {
            const colors = colorSettings[currentCard];
            document.getElementById('bgColorPicker').value = colors.background;
            document.getElementById('labelColorPicker').value = colors.label;
            document.getElementById('messageColorPicker').value = colors.message;
        }
        
        applyColors();
        closeColorDialog();
    }
}

function closeColorDialog() {
    document.getElementById('colorDialog').style.display = 'none';
}

// Test mode functions
let testTimes = [];
let testIndex = 0;
let countdownSeconds = 0;

function startTest() {
    if (isTestMode) {
        if (!confirm('Test is running. Stop current test and start new one?')) {
            return;
        }
        stopTest();
    }

    const password = prompt("Enter password to start test mode:");
    if (password !== 'shs') {
        alert('Invalid password');
        return;
    }

    // Use array of test times instead of reading from file
    testTimes = [
        "06:45",     // Before school
        "07:15",     // Before warning bell
        "07:22",     // During warning bell
        "07:24",     // Warning bell → Period 1
        "07:30",     // During Period 1
        "08:11",     // Period 1 → Period 2
        "08:30",     // During Period 2
        "09:39",     // During Period 4
        "11:07",     // Period 5 → Period 6
        "12:35",     // During Period 8
        "13:19",     // Period 8 → Period 9
        "14:03",     // Period 9 → Extra Help
        "14:15",     // During Extra Help
        "14:31"      // After school
    ];
    
    testIndex = 0;
    isTestMode = true;
    document.getElementById('testStatus').style.display = 'block';
    
    // Clear the normal update interval
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
    
    // Start test interval
    testInterval = setInterval(runTest, 2000);
    runTest(); // Run immediately
}

function runTest() {
    if (testIndex < testTimes.length) {
        const testTime = testTimes[testIndex].trim();
        document.getElementById('testMessage').textContent = `Testing with time: ${testTime}`;
        updateDisplay(testTime);
        setTimeout(() => {
            testIndex++; // Increment after a delay
        }, 1900); // Slightly less than the test interval (2000ms)
    } else {
        stopTest();
        countdownSeconds = 5;
        const countdownInterval = setInterval(() => {
            if (countdownSeconds > 0) {
                document.getElementById('testMessage').textContent = 
                    `Returning to normal operation in ${countdownSeconds} seconds`;
                countdownSeconds--;
            } else {
                document.getElementById('testStatus').style.display = 'none';
                clearInterval(countdownInterval);
            }
        }, 1000);
    }
}

function stopTest() {
    isTestMode = false;
    if (testInterval) clearInterval(testInterval);
    document.getElementById('testStatus').style.display = 'none';
    updateInterval = setInterval(updateDisplay, 60000);
    updateDisplay();
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add schedule card click listeners
    document.querySelector('.schedule-card:nth-child(1)').addEventListener('click', 
        () => showColorDialog('regular'));
    document.querySelector('.schedule-card:nth-child(2)').addEventListener('click', 
        () => showColorDialog('two_hour_delay'));
    document.querySelector('.schedule-card:nth-child(3)').addEventListener('click', 
        () => showColorDialog('homeroom'));

    // Add color dialog button listeners
    document.getElementById('saveColors').addEventListener('click', saveColors);
    document.getElementById('cancelColors').addEventListener('click', closeColorDialog);
    document.getElementById('resetColors').addEventListener('click', resetColors);

    // Add test mode listeners
    document.querySelector('header').addEventListener('click', startTest);
    document.getElementById('stopTest').addEventListener('click', stopTest);

    // Initialize color settings
    initializeColorSettings();

    // Start regular updates
    updateDisplay();
    updateInterval = setInterval(updateDisplay, 60000);
}); 