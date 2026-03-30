/**
 * build_pipeline.groovy
 * Groovy CI/CD build pipeline for the SC2 Zerg bot.
 *
 * Stages:
 *   1. validate  – syntax-check all Python source files
 *   2. test      – run pytest suite and collect coverage
 *   3. package   – bundle bot into a deployable arena archive
 *   4. deploy    – upload archive to the ladder / arena server
 *
 * Run standalone:  groovy build_pipeline.groovy
 * Use as Jenkins Shared Library by calling BotBuildPipeline.run()
 */

class BotBuildPipeline {

    // ---------- configuration ----------
    static final String BOT_NAME      = "지휘관봇"
    static final String SRC_DIR       = "src"
    static final String TESTS_DIR     = "tests"
    static final String DIST_DIR      = "dist"
    static final String ARENA_ENDPOINT = System.getenv("ARENA_URL") ?: "http://localhost:8080/upload"

    // Accumulate per-stage results for the final summary
    List<Map> stageResults = []

    // ---------- pipeline entry point ----------
    /**
     * Execute all pipeline stages in order.
     * Aborts on first failure unless continueOnError is set.
     */
    void run(boolean continueOnError = false) {
        println "=== ${BOT_NAME} Build Pipeline starting ==="
        println "Timestamp: ${new Date()}\n"

        [
            { validate() },
            { test()     },
            { packageBot() },
            { deploy()   }
        ].each { stage ->
            try {
                stage()
            } catch (Exception e) {
                println "[FATAL] Stage aborted: ${e.message}"
                if (!continueOnError) {
                    printSummary()
                    System.exit(1)
                }
            }
        }

        printSummary()
    }

    // ---------- stage 1: validate ----------
    /**
     * Run `python -m py_compile` on every .py file under SRC_DIR.
     * Fast syntax gate – catches import-level errors before tests run.
     */
    void validate() {
        def stageName = "validate"
        println "--- [1/4] Syntax Validation ---"

        def pyFiles = new FileNameFinder().getFileNames(SRC_DIR, "**/*.py")
        if (pyFiles.isEmpty()) {
            record stageName, "SKIP", "No Python files found in ${SRC_DIR}"
            return
        }

        def failures = []
        pyFiles.each { f ->
            def result = exec("python -m py_compile \"${f}\"")
            if (result.exitCode != 0) {
                failures << "${f}: ${result.stderr.trim()}"
            }
        }

        if (failures) {
            record stageName, "FAIL", failures.join("\n")
            throw new RuntimeException("Syntax errors detected in ${failures.size()} file(s)")
        }

        record stageName, "PASS", "All ${pyFiles.size()} file(s) are syntax-clean"
        println "  OK – ${pyFiles.size()} files validated"
    }

    // ---------- stage 2: test ----------
    /**
     * Execute pytest with coverage reporting.
     * Fail the stage if coverage drops below 70 %.
     */
    void test() {
        def stageName = "test"
        println "--- [2/4] pytest + Coverage ---"

        def result = exec(
            "python -m pytest ${TESTS_DIR} --tb=short " +
            "--cov=${SRC_DIR} --cov-report=term-missing " +
            "--cov-fail-under=70 -q"
        )

        if (result.exitCode != 0) {
            record stageName, "FAIL", result.stdout.readLines().last()
            throw new RuntimeException("Tests failed (exit ${result.exitCode})")
        }

        // Parse "X passed" line from pytest output
        def summary = result.stdout.readLines().find { it =~ /\d+ passed/ } ?: "tests passed"
        record stageName, "PASS", summary
        println "  OK – ${summary}"
    }

    // ---------- stage 3: package ----------
    /**
     * Create dist/ directory and zip the bot source into a versioned archive.
     */
    void packageBot() {
        def stageName = "package"
        println "--- [3/4] Packaging ---"

        def version   = "v${new Date().format('yyyyMMdd-HHmm')}"
        def archiveName = "${BOT_NAME}-${version}.zip"

        new File(DIST_DIR).mkdirs()

        def result = exec("python -m zipfile -c ${DIST_DIR}/${archiveName} ${SRC_DIR}/")

        if (result.exitCode != 0) {
            record stageName, "FAIL", result.stderr.trim()
            throw new RuntimeException("Packaging failed")
        }

        record stageName, "PASS", "Created ${DIST_DIR}/${archiveName}"
        println "  OK – ${DIST_DIR}/${archiveName}"
    }

    // ---------- stage 4: deploy ----------
    /**
     * Upload the latest archive to the arena server via curl.
     * Skipped if ARENA_URL env-var is not set (local builds).
     */
    void deploy() {
        def stageName = "deploy"
        println "--- [4/4] Deploy to Arena ---"

        if (!System.getenv("ARENA_URL")) {
            record stageName, "SKIP", "ARENA_URL not set – skipping deploy"
            println "  SKIP – set ARENA_URL to enable deployment"
            return
        }

        def archive = new FileNameFinder().getFileNames(DIST_DIR, "*.zip").sort().last()
        def result  = exec("curl -sf -F file=@${archive} ${ARENA_ENDPOINT}")

        if (result.exitCode != 0) {
            record stageName, "FAIL", result.stderr.trim()
            throw new RuntimeException("Deploy upload failed")
        }

        record stageName, "PASS", "Uploaded ${archive} to ${ARENA_ENDPOINT}"
        println "  OK – deployed ${archive}"
    }

    // ---------- helpers ----------
    private void record(String stage, String status, String detail) {
        stageResults << [stage: stage, status: status, detail: detail]
    }

    private void printSummary() {
        println "\n=== Build Summary ==="
        stageResults.each { r ->
            println "  [${r.status.padRight(4)}] ${r.stage.padRight(12)} ${r.detail}"
        }
        println "===================="
    }

    /**
     * Execute a shell command and return [exitCode, stdout, stderr].
     */
    private Map exec(String cmd) {
        def proc = cmd.execute()
        def out  = new StringBuffer()
        def err  = new StringBuffer()
        proc.consumeProcessOutput(out, err)
        proc.waitFor()
        [exitCode: proc.exitValue(), stdout: out.toString(), stderr: err.toString()]
    }
}

// ---------- Standalone entry point ----------
new BotBuildPipeline().run()
