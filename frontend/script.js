const API_URL = 'http://127.0.0.1:5000/api/compile';

const compileBtn = document.getElementById('compile-btn');
const sourceCodeInput = document.getElementById('source-code');
const testInputInput = document.getElementById('test-input');
const sourceLangSelect = document.getElementById('source-lang');
const targetLangSelect = document.getElementById('target-lang');
const validateCheck = document.getElementById('validate-check');
const errorBox = document.getElementById('error-box');
const artifactContent = document.getElementById('artifact-content');

// We map the step IDs to their corresponding artifact payload keys
const stepToArtifactMap = {
    'preprocessing': { target: 'preprocessed', title: 'Preprocessor: Cleaned Source' },
    'lexical_analysis': { target: 'tokens', title: 'Lexer: Tokens Array' },
    'syntax_analysis': { target: 'ast', title: 'Parser: Abstract Syntax Tree' },
    'semantic_analysis': { target: 'symbols', title: 'Semantic: Symbol Table' },
    'ir_generation': { target: 'ir', title: 'IR Generation: Three Address Code' },
    'optimization': { target: 'optimized_ir', title: 'Optimizer: Optimized TAC' },
    'code_generation': { target: 'output_code', title: 'CodeGen: Target Output Source' },
    'validation': { target: 'validation_report', title: 'Validation Report' }
};

let currentArtifacts = {};
let currentTarget = 'output_code';
const viewerTitle = document.getElementById('viewer-title');

function renderArtifact() {
    if (!currentArtifacts || Object.keys(currentArtifacts).length === 0) {
        artifactContent.textContent = "Compile a program to view artifacts here...";
        return;
    }

    if (currentTarget === 'validation_report') {
        const valData = currentArtifacts._validation;
        if (!valData || Object.keys(valData).length === 0) {
            artifactContent.innerHTML = "Validation was not run.";
            return;
        }
        
        const passedHTML = valData.passed 
            ? `<span style="color: var(--accent-green); font-weight: bold;">✅ PASSED</span>`
            : `<span style="color: var(--accent-red); font-weight: bold;">❌ FAILED</span>`;
            
        artifactContent.innerHTML = `
<div style="font-family: 'Inter', sans-serif;">
    <h3 style="margin-bottom: 20px;">Validation Result: ${passedHTML}</h3>
    
    <div style="margin-bottom: 15px;">
        <strong style="color: var(--primary-cyan);">Expected Output (From Source Code):</strong>
        <pre style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; margin-top: 5px; color: #fff;">${valData.source_output || '<i>(No Output)</i>'}</pre>
    </div>

    <div>
        <strong style="color: var(--primary-cyan);">Actual Output (From Target Generated Code):</strong>
        <pre style="background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; margin-top: 5px; color: #fff;">${valData.target_output || '<i>(No Output)</i>'}</pre>
    </div>
</div>
        `;
    } else if (currentTarget === 'output_code') {
        artifactContent.textContent = currentArtifacts.output_code || "No output code generated.";
    } else {
        artifactContent.textContent = currentArtifacts[currentTarget] || "Artifact not found.";
    }
}

// Reset Timeline Graphic
function resetTimeline() {
    const steps = document.querySelectorAll('.step');
    steps.forEach(step => {
        step.classList.remove('success', 'failed');
    });
}

// Update Timeline Graphic
function updateTimeline(phasesData, failedPhase = null) {
    const stepIds = [
        'preprocessing',
        'lexical_analysis',
        'syntax_analysis',
        'semantic_analysis',
        'ir_generation',
        'optimization',
        'code_generation',
        'validation'
    ];

    stepIds.forEach(id => {
        const stepEl = document.getElementById(`step-${id}`);
        if (!stepEl) return;
        
        if (phasesData && phasesData[id] === 'success') {
            stepEl.classList.add('success');
            
            // Add click listener purely for SUCCESSFUL phases to view their artifact!
            stepEl.onclick = () => {
                const mapData = stepToArtifactMap[id];
                if (mapData) {
                    currentTarget = mapData.target;
                    viewerTitle.textContent = mapData.title;
                    renderArtifact();
                } else {
                    currentTarget = null;
                    viewerTitle.textContent = "Pipeline Output";
                    artifactContent.textContent = "No visual artifact explicitly saved for this internal phase.";
                }
            };
            
        } else if (id === failedPhase || (phasesData && phasesData[id] === 'failed')) {
            stepEl.classList.add('failed');
            stepEl.onclick = null; // Prevent opening failed artifacts!
        } else {
            stepEl.onclick = null; // Prevent opening skipped/unrun artifacts
        }
    });
}

// Compile Event
compileBtn.addEventListener('click', async () => {
    const sourceCode = sourceCodeInput.value.trim();
    if (!sourceCode) {
        showError("Please enter some source code to compile.");
        return;
    }

    compileBtn.textContent = 'COMPILING...';
    compileBtn.style.opacity = '0.7';
    compileBtn.style.pointerEvents = 'none';
    
    hideError();
    resetTimeline();
    artifactContent.textContent = "Loading...";

    const payload = {
        source_code: sourceCode,
        source_lang: sourceLangSelect.value,
        target_lang: targetLangSelect.value,
        test_input: testInputInput.value,
        validate: validateCheck.checked
    };

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            currentArtifacts = data.artifacts || {};
            if (data.validation) {
                currentArtifacts._validation = data.validation;
            }
            updateTimeline(data.phases);
            
            // On full success, show Code Output AND Validation simultaneously on the main page.
            currentTarget = 'output_code';
            viewerTitle.textContent = 'CodeGen: Target Output Source';
            renderArtifact();
            
        } else {
            console.error(data);
            showError(`Phase: ${data.phase}\nError: ${data.message}\nLine: ${data.line}, Col: ${data.column}`);
            // Extract the completed artifacts up to point of failure to allow inspection
            currentArtifacts = data.artifacts || {};
            
            // Map the exact string format to visually sync the failing timeline bubble
            const formattedPhaseId = data.phase.toLowerCase().replace(' ', '_');
            
            // Highlight the failed phase dynamically and lock its artifacts
            updateTimeline(data.phases || {}, formattedPhaseId);
            
            // Load code target by default so they see whatever errored out
            currentTarget = 'output_code';
            viewerTitle.textContent = "Pipeline Output";
            renderArtifact();
        }

    } catch (error) {
        console.error("Network Error:", error);
        showError("Could not connect to the Backend API. Ensure python api/app.py is running on port 5000.");
    } finally {
        compileBtn.textContent = 'COMPILE';
        compileBtn.style.opacity = '1';
        compileBtn.style.pointerEvents = 'auto';
    }
});

function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.remove('hidden');
}

function hideError() {
    errorBox.classList.add('hidden');
}

// Pre-fill dummy code based on source selection
sourceLangSelect.addEventListener('change', () => {
    if (sourceCodeInput.value.trim().length > 0) return;
    
    if (sourceLangSelect.value === 'cpp') {
        sourceCodeInput.value = `#include <iostream>\nusing namespace std;\n\nint main() {\n    int a = 10;\n    int b = 20;\n    int sum = a + b;\n    cout << sum << endl;\n    return 0;\n}`;
    }
});
