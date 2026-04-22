import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_NAME = 'verifyiq-api-regression';
const PROJECT_SPACE = 'projects/verifyiq-api-regression';
const SESSION_MARKER = '## VerifyIQ Mind Session';
const GLOBAL_MIND_PLUGIN = `${process.env.HOME ?? ''}/.config/opencode/plugins/mind-automation.js`;

const pluginFile = fileURLToPath(import.meta.url);
const pluginDir = dirname(pluginFile);
const repoRoot = dirname(dirname(pluginDir));
const wrapperPath = join(repoRoot, 'tools', 'mind_session.py');
const repoPython = join(repoRoot, '.venv', 'bin', 'python');

let queued = Promise.resolve();

function enqueue(task) {
  const next = queued.then(task, task);
  queued = next.then(
    () => undefined,
    () => undefined,
  );
  return next;
}

function buildPythonCommand() {
  if (existsSync(repoPython)) {
    return repoPython;
  }
  return 'python3';
}

function buildEnv() {
  const existingPath = process.env.PATH ?? '';
  const extras = [
    `${process.env.HOME ?? ''}/.local/bin`,
    `${process.env.HOME ?? ''}/.bun/bin`,
  ].filter(Boolean);
  return {
    ...process.env,
    PATH: [...extras, existingPath].filter(Boolean).join(':'),
  };
}

function isVerifyiqContext(ctx) {
  const candidates = [ctx?.worktree, ctx?.directory].filter(
    (value) => typeof value === 'string' && value.length > 0,
  );
  if (candidates.length === 0) {
    return basename(repoRoot) === REPO_NAME;
  }
  return candidates.some((value) => basename(value) === REPO_NAME || value.includes(`/${REPO_NAME}`));
}

function parsePayload(stdout) {
  const lines = String(stdout ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  for (let index = lines.length - 1; index >= 0; index -= 1) {
    try {
      return JSON.parse(lines[index]);
    } catch {
      continue;
    }
  }
  return null;
}

function runWrapper(command, extraArgs = []) {
  if (!existsSync(wrapperPath)) {
    return {
      ok: false,
      error: `Missing wrapper: ${wrapperPath}`,
    };
  }

  const result = spawnSync(buildPythonCommand(), [wrapperPath, command, ...extraArgs], {
    cwd: repoRoot,
    env: buildEnv(),
    encoding: 'utf-8',
  });

  const payload = parsePayload(result.stdout);
  if (result.status === 0 && payload && payload.status === 'ok') {
    return {
      ok: true,
      payload,
    };
  }

  return {
    ok: false,
    error: (payload && payload.error) || String(result.stderr || result.stdout || 'wrapper call failed').trim(),
    payload,
  };
}

function compactSystemContext(text) {
  const normalized = String(text ?? '').trim();
  if (!normalized) {
    return '';
  }
  return `${SESSION_MARKER}\nProject space: ${PROJECT_SPACE}\n${normalized}`;
}

function shouldInjectPromptContext() {
  return !existsSync(GLOBAL_MIND_PLUGIN);
}

export const VerifyiqMindSessionPlugin = async (ctx) => {
  const sessionState = new Map();
  let doctorChecked = false;
  let automationReady = false;

  const ensureReady = () => {
    if (!isVerifyiqContext(ctx)) {
      return false;
    }
    if (doctorChecked) {
      return automationReady;
    }
    doctorChecked = true;
    const result = runWrapper('doctor');
    automationReady = result.ok;
    return automationReady;
  };

  const rememberContext = (sessionID, payload) => {
    if (!sessionID || !payload?.context) {
      return;
    }
    const entry = sessionState.get(sessionID) ?? { injected: false };
    entry.context = compactSystemContext(payload.context);
    entry.injected = false;
    sessionState.set(sessionID, entry);
  };

  const runStart = (sessionID, eventType) => {
    const args = [];
    if (sessionID) {
      args.push('--session-id', sessionID);
    }
    if (eventType) {
      args.push('--event', eventType);
    }
    const result = runWrapper('start', args);
    if (result.ok) {
      rememberContext(sessionID, result.payload);
    }
  };

  const runCheckpoint = (sessionID, eventType) => {
    const args = [];
    if (sessionID) {
      args.push('--session-id', sessionID);
    }
    if (eventType) {
      args.push('--event', eventType);
    }
    runWrapper('checkpoint', args);
  };

  const runFinish = (sessionID, eventType) => {
    const args = [];
    if (sessionID) {
      args.push('--session-id', sessionID);
    }
    if (eventType) {
      args.push('--event', eventType);
    }
    runWrapper('finish', args);
    if (sessionID) {
      sessionState.delete(sessionID);
    }
  };

  return {
    event: async ({ event }) => {
      await enqueue(async () => {
        if (!ensureReady() || !event || typeof event !== 'object') {
          return;
        }

        const sessionID = typeof event.sessionID === 'string'
          ? event.sessionID
          : typeof event.id === 'string'
            ? event.id
            : typeof event.session?.id === 'string'
              ? event.session.id
              : undefined;

        if (event.type === 'session.created' || event.type === 'workspace.restore') {
          runStart(sessionID, event.type);
          return;
        }

        if (event.type === 'session.compacted') {
          runStart(sessionID, event.type);
          return;
        }

        if (event.type === 'session.idle') {
          runCheckpoint(sessionID, event.type);
          return;
        }

        if (event.type === 'session.deleted') {
          runFinish(sessionID, event.type);
        }
      });
    },

    'experimental.session.compacting': async (input, output) => {
      await enqueue(async () => {
        if (!ensureReady()) {
          return;
        }
        runCheckpoint(input?.sessionID, 'experimental.session.compacting');
      });

      if (shouldInjectPromptContext() && Array.isArray(output?.context)) {
        output.context.push(
          '## VerifyIQ Mind Continuity',
          '- Repo-controlled Mind checkpointing ran before compaction.',
          '- Post-compaction context recovery will be restored automatically when available.',
        );
      }
    },

    'experimental.chat.system.transform': async (input, output) => {
      if (!shouldInjectPromptContext() || !ensureReady() || !Array.isArray(output?.system) || output.system.length === 0) {
        return;
      }

      const sessionID = typeof input?.sessionID === 'string' ? input.sessionID : 'session-unknown';
      let entry = sessionState.get(sessionID);

      if (!entry?.context) {
        await enqueue(async () => {
          runStart(sessionID, 'experimental.chat.system.transform');
        });
        entry = sessionState.get(sessionID);
      }

      if (!entry?.context || entry.injected) {
        return;
      }

      const lastIndex = output.system.length - 1;
      if (!output.system[lastIndex].includes(SESSION_MARKER)) {
        output.system[lastIndex] += `\n\n${entry.context}`;
      }

      entry.injected = true;
      sessionState.set(sessionID, entry);
    },
  };
};

export default VerifyiqMindSessionPlugin;
