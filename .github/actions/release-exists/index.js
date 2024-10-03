const core = require('@actions/core');
const github = require('@actions/github');

async function checkRelease() {
    const tag = core.getInput('tag', { required: true });
    const repository = core.getInput('repository');
    const token = core.getInput('token');
    console.log(`Searching release with tag ${tag} in ${repository}`);
    const [owner, repo] = repository.split("/");
    const octokit = github.getOctokit(token)
    try {
        const reply = await octokit.request("GET /repos/{owner}/{repo}/releases/tags/{tag}", {
            owner: owner,
            repo: repo,
            tag: tag,
        });
        if (reply.status === 200) {
            console.log(`Release ${tag} found`);
            return true;
        }
    } catch (error) {
        console.log(`Release ${tag} not found`);
    }
    return false;
}

async function run() {
    try {
        const exists = await checkRelease();
        core.setOutput('exists', exists);
    } catch (error) {
        core.setFailed(error.message);
    }
}

run();
