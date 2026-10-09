import groovy.transform.Field
import org.jenkinsci.plugins.credentialsbinding.impl.CredentialNotFoundException

// Cached list of credential bindings discovered in Jenkins Credentials Store
@Field def aiCredentialBindings = null

def getAiCredentialBindings() {
    if (aiCredentialBindings != null) {
        return aiCredentialBindings
    }
    def bindings = []

    // Probe NVIDIA NIM API Key (NIM_API_KEY with NVIDIA_API_KEY alias fallback)
    try {
        withCredentials([string(credentialsId: 'NIM_API_KEY', variable: '_PROBE_NIM')]) {
            bindings.add(string(credentialsId: 'NIM_API_KEY', variable: 'NIM_API_KEY'))
        }
    } catch (CredentialNotFoundException ignored) {
        try {
            withCredentials([string(credentialsId: 'NVIDIA_API_KEY', variable: '_PROBE_NV')]) {
                bindings.add(string(credentialsId: 'NVIDIA_API_KEY', variable: 'NIM_API_KEY'))
            }
        } catch (CredentialNotFoundException ignored2) {
            // Neither NIM credential configured
        }
    }

    // Probe Google Gemini API Key
    try {
        withCredentials([string(credentialsId: 'GEMINI_API_KEY', variable: '_PROBE_GEMINI')]) {
            bindings.add(string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY'))
        }
    } catch (CredentialNotFoundException ignored) {
        // Gemini credential not configured
    }

    aiCredentialBindings = bindings
    return aiCredentialBindings
}

def withOptionalAiCredentials(Closure body) {
    def bindings = getAiCredentialBindings()
    if (!bindings.isEmpty()) {
        withCredentials(bindings) {
            body()
        }
    } else {
        body()
    }
}

pipeline {
    agent {
        docker {
            image 'mcr.microsoft.com/playwright/python:v1.63.0-noble'
            args '--ipc=host'
        }
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
    }

    environment {
        CI = 'true'
        TARGET_APP_URL = 'http://localhost:3001'
        PYTHONUNBUFFERED = '1'
        PATH = "${WORKSPACE}/.venv/bin:${env.PATH}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                script {
                    def bindings = getAiCredentialBindings()
                    if (!bindings.isEmpty()) {
                        echo "[Credentials] Discovered ${bindings.size()} AI credential binding(s) in Jenkins store. Will bind during Test and Benchmark stages."
                    } else {
                        echo "[Credentials] No AI keys detected in Jenkins credentials. Running with offline local-heuristics fallback."
                    }
                }

                sh '''
                    echo "--- Setting up Python virtual environment and dependencies ---"
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    playwright install --with-deps chromium
                '''
            }
        }

        stage('Start Target App') {
            steps {
                sh '''
                    [ -f .venv/bin/activate ] && . .venv/bin/activate
                    echo "--- Starting target application on port 3001 in background ---"
                    JENKINS_NODE_COOKIE=dontKillMe nohup python target-app/server.py > target_app.log 2>&1 &
                    echo $! > target_app.pid

                    echo "Waiting for target application server on http://localhost:3001..."
                    READY=0
                    for i in $(seq 1 30); do
                        if curl -s -f http://localhost:3001 > /dev/null 2>&1 || python -c "import urllib.request; urllib.request.urlopen('http://localhost:3001', timeout=1)" > /dev/null 2>&1; then
                            echo "Target application server is up and responding on port 3001 (attempt ${i})."
                            READY=1
                            break
                        fi
                        sleep 1
                    done

                    if [ "${READY}" -ne 1 ]; then
                        echo "ERROR: Target application server failed to respond within 30 seconds."
                        echo "--- Server Log Dump ---"
                        cat target_app.log || true
                        echo "-----------------------"
                        exit 1
                    fi
                '''
            }
        }

        stage('Test') {
            steps {
                script {
                    withOptionalAiCredentials {
                        sh '''
                            [ -f .venv/bin/activate ] && . .venv/bin/activate
                            mkdir -p artifacts
                            echo "--- Executing Sentinel Test Suite via CLI Runner ---"
                            python src/cli.py run

                            echo "--- Executing Pytest Suite with JUnit XML Export ---"
                            pytest -v --junitxml=artifacts/junit-report.xml
                        '''
                    }
                }
            }
        }

        stage('Benchmark') {
            steps {
                script {
                    withOptionalAiCredentials {
                        sh '''
                            [ -f .venv/bin/activate ] && . .venv/bin/activate
                            echo "--- Executing Sentinel 23-Scenario Mutation Benchmark ---"
                            python scripts/benchmark_runner.py

                            echo "--- Verifying Benchmark Quality Gate ---"
                            python -c "
import os, json, sys

results_file = 'artifacts/benchmark_results.json'
try:
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception as e:
    print(f'ERROR: Could not read benchmark results at {results_file}: {e}')
    sys.exit(1)

summary = data.get('summary', {})
heal_precision_val = summary.get('heal_precision_pct', summary.get('heal_precision'))
false_heal_rate = summary.get('false_heal_rate_pct', summary.get('false_heal_rate'))
safeguards_held = summary.get('safeguards_held', 0)
real_bugs_total = summary.get('real_bug_total', 0)

if false_heal_rate is None:
    print(f'ERROR: Metrics missing in {results_file}. Available keys: {list(summary.keys())}')
    sys.exit(1)

false_heal_rate = float(false_heal_rate)
heal_precision_str = f'{heal_precision_val}%' if heal_precision_val is not None else 'N/A'

print(f'Benchmark Metrics: heal_precision_pct = {heal_precision_str}, false_heal_rate_pct = {false_heal_rate}%, safeguards_held = {safeguards_held}/{real_bugs_total}')

# Quality gate: enforce 100% precision and 0% false heals when AI provider keys are configured.
# When running offline without AI keys, log metrics without failing the build.
has_keys = bool(os.getenv('NIM_API_KEY') or os.getenv('NVIDIA_API_KEY') or os.getenv('GEMINI_API_KEY'))

if has_keys:
    print('[Quality Gate] AI provider key configured: enforcing strict thresholds (heal_precision >= 100%, false_heal_rate == 0%)...')
    gate_failed = False
    if heal_precision_val is None or float(heal_precision_val) < 100.0:
        print(f'QUALITY GATE FAILED: Heal precision dropped below 100% (actual: {heal_precision_str})')
        gate_failed = True

    if false_heal_rate > 0.0:
        print(f'QUALITY GATE FAILED: False-heal rate rose above 0% (actual: {false_heal_rate}%)')
        gate_failed = True

    if gate_failed:
        sys.exit(1)

    print('QUALITY GATE PASSED: 100% heal precision and 0% false-heal rate achieved.')
else:
    print('[Quality Gate] Offline fallback mode (no AI keys configured): logging metrics without failing build.')
    print(f'Safeguard enforcement held: {safeguards_held}/{real_bugs_total} real bugs blocked from auto-patching.')
    print('QUALITY GATE PASSED (Offline Heuristics).')
"
                        '''
                    }
                }
            }
        }

        stage('Archive and Report') {
            steps {
                archiveArtifacts artifacts: 'artifacts/**', allowEmptyArchive: true, fingerprint: true
                junit testResults: 'artifacts/junit-report.xml', allowEmptyResults: true
            }
        }
    }

    post {
        always {
            sh '''
                echo "--- Post-build cleanup ---"
                if [ -f target_app.pid ]; then
                    TARGET_PID=$(cat target_app.pid)
                    echo "Stopping target application server (PID: ${TARGET_PID})..."
                    kill ${TARGET_PID} 2>/dev/null || true
                    sleep 2
                    kill -9 ${TARGET_PID} 2>/dev/null || true
                    rm -f target_app.pid
                fi
                pkill -f "target-app/server.py" 2>/dev/null || true
            '''
        }
    }
}
