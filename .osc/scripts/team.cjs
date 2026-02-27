#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execSync } = require('node:child_process');

// ---------------------------------------------------------------------------
// Path helpers (mirrors common/paths.sh)
// ---------------------------------------------------------------------------

const DIR_OSC = '.osc';
const DIR_TEAMS = 'teams';
const DIR_TEAM_TEMPLATES = 'team-templates';
const DIR_AGENTS = 'agents';

function oscRepoRoot() {
  let current = process.cwd();
  while (current !== path.dirname(current)) {
    if (fs.existsSync(path.join(current, DIR_OSC))) return current;
    current = path.dirname(current);
  }
  try {
    return execSync('git rev-parse --show-toplevel', { encoding: 'utf8' }).trim();
  } catch {
    return process.cwd();
  }
}

function oscDir(root) { return path.join(root || oscRepoRoot(), DIR_OSC); }
function teamsDir(root) { return path.join(oscDir(root), DIR_TEAMS); }
function templatesDir(root) { return path.join(oscDir(root), DIR_TEAM_TEMPLATES); }
function agentsDir(root) { return path.join(oscDir(root), DIR_AGENTS); }

// ---------------------------------------------------------------------------
// Runtime detection (mirrors common/runtime.sh)
// ---------------------------------------------------------------------------

function detectRuntime() {
  if (process.env.OSC_RUNTIME) return process.env.OSC_RUNTIME;
  try { execSync('which claude', { stdio: 'ignore' }); return 'claude'; } catch {}
  try { execSync('which codex', { stdio: 'ignore' }); return 'codex'; } catch {}
  return 'unknown';
}

// ---------------------------------------------------------------------------
// YAML parser (handles the subset used by team templates and agent defs)
// ---------------------------------------------------------------------------
/**
 * Minimal YAML parser for the subset used by team templates and agent defs.
 * Handles: scalars, lists (block & inline [a,b]), nested maps, comments,
 * quoted strings, and block scalars (|, >).
 * Does NOT handle: anchors, tags, flow mappings.
 */
function parseYaml(text) {
  const lines = text.split('\n');
  // Each stack entry: { indent, container, key? }
  // container is the object/array we're currently populating
  // key is set when the container is a parent object and we just created a child list
  const root = {};
  const stack = [{ indent: -2, container: root }];

  function top() { return stack[stack.length - 1]; }

  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    const stripped = stripComment(raw);
    const trimmed = stripped.trimEnd();
    if (!trimmed.trim()) continue;

    // Calculate real indent (position of first non-space char)
    const indent = trimmed.search(/\S/);
    if (indent < 0) continue;

    // Pop stack entries that are at same or deeper indent
    while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
      stack.pop();
    }

    const content = trimmed.slice(indent);

    // --- List item: "- ..." ---
    if (content.startsWith('- ')) {
      const itemContent = content.slice(2).trim();
      // Find the array to push into
      let arr = null;
      const t = top();
      if (Array.isArray(t.container)) {
        arr = t.container;
      }
      if (!arr) continue;

      if (itemContent.includes(':')) {
        // Map item in list: "- agent: plan"
        const obj = {};
        const kv = splitKV(itemContent);
        if (kv) {
          const { key, rawValue } = kv;
          if (rawValue === '|' || rawValue === '>') {
            const block = readBlockScalar(lines, i + 1, indent, rawValue);
            obj[key] = block.value;
            i = block.nextIndex;
          } else {
            assignYamlValue(obj, key, rawValue);
          }
        }
        arr.push(obj);
        // Properties of this map item will be at indent + 2 or more
        stack.push({ indent: indent + 1, container: obj });
      } else {
        arr.push(parseScalar(itemContent));
      }
      continue;
    }

    // --- Key: value ---
    const colonIdx = content.indexOf(':');
    if (colonIdx > 0) {
      const key = content.slice(0, colonIdx).trim();
      const rest = content.slice(colonIdx + 1).trim();
      const t = top();
      const target = (typeof t.container === 'object' && !Array.isArray(t.container)) ? t.container : null;
      if (!target) continue;

      if (!rest) {
        // Empty value — peek to see if it's a list or map
        const nextLine = peekNextNonEmpty(lines, i + 1);
        const nextTrimmed = nextLine ? nextLine.trimStart() : '';
        if (nextTrimmed.startsWith('- ')) {
          target[key] = [];
          stack.push({ indent: indent + 1, container: target[key] });
        } else {
          target[key] = {};
          stack.push({ indent: indent + 1, container: target[key] });
        }
      } else if (rest === '|' || rest === '>') {
        const block = readBlockScalar(lines, i + 1, indent, rest);
        target[key] = block.value;
        i = block.nextIndex;
      } else if (rest.startsWith('[') && rest.endsWith(']')) {
        target[key] = rest.slice(1, -1).split(',').map(s => parseScalar(s.trim())).filter(s => s !== '');
      } else {
        target[key] = parseScalar(rest);
      }
    }
  }
  return root;
}

function stripComment(line) {
  let inSingle = false, inDouble = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === "'" && !inDouble) inSingle = !inSingle;
    else if (ch === '"' && !inSingle) inDouble = !inDouble;
    else if (ch === '#' && !inSingle && !inDouble && (i === 0 || line[i - 1] === ' ')) {
      return line.slice(0, i);
    }
  }
  return line;
}

function peekNextNonEmpty(lines, start) {
  for (let i = start; i < lines.length; i++) {
    const t = lines[i].trim();
    if (t && !t.startsWith('#')) return lines[i];
  }
  return null;
}

function parseScalar(s) {
  if (!s) return '';
  // Remove quotes
  if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
    return s.slice(1, -1);
  }
  if (s === 'true') return true;
  if (s === 'false') return false;
  if (s === 'null') return null;
  if (/^-?\d+$/.test(s)) return parseInt(s, 10);
  if (/^-?\d+\.\d+$/.test(s)) return parseFloat(s);
  return s;
}

function parseKV(str, obj) {
  const kv = splitKV(str);
  if (!kv) return;
  assignYamlValue(obj, kv.key, kv.rawValue);
}

function splitKV(str) {
  const idx = str.indexOf(':');
  if (idx <= 0) return null;
  return {
    key: str.slice(0, idx).trim(),
    rawValue: str.slice(idx + 1).trim(),
  };
}

function assignYamlValue(obj, key, rawValue) {
  if (rawValue.startsWith('[') && rawValue.endsWith(']')) {
    obj[key] = rawValue.slice(1, -1).split(',').map(s => parseScalar(s.trim())).filter(s => s !== '');
  } else {
    obj[key] = parseScalar(rawValue);
  }
}

function readBlockScalar(lines, startIndex, parentIndent, style) {
  const consumed = [];
  let minIndent = null;
  let i = startIndex;

  for (; i < lines.length; i++) {
    const raw = lines[i];
    const trimmed = raw.trimEnd();
    const lineContent = trimmed.trim();

    if (!lineContent) {
      consumed.push({ blank: true, text: '' });
      continue;
    }

    const indent = trimmed.search(/\S/);
    if (indent <= parentIndent) break;

    if (minIndent === null || indent < minIndent) {
      minIndent = indent;
    }
    consumed.push({ blank: false, text: trimmed, indent });
  }

  if (minIndent === null) {
    return { value: '', nextIndex: i - 1 };
  }

  const normalized = consumed.map((entry) => {
    if (entry.blank) return '';
    return entry.text.slice(minIndent);
  });

  const value = style === '>' ? foldBlockLines(normalized) : normalized.join('\n');
  return { value, nextIndex: i - 1 };
}

function foldBlockLines(lines) {
  let out = '';
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line === '') {
      out += '\n';
      continue;
    }
    out += line;
    if (i >= lines.length - 1) continue;
    const next = lines[i + 1];
    out += next === '' ? '\n' : ' ';
  }
  return out;
}

// ---------------------------------------------------------------------------
// JSON helpers
// ---------------------------------------------------------------------------

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n');
}

function nowISO() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function mkdirp(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

// ---------------------------------------------------------------------------
// Process helpers
// ---------------------------------------------------------------------------

function pidAlive(pid) {
  if (!pid) return false;
  try { process.kill(pid, 0); return true; } catch { return false; }
}

function killPid(pid, signal) {
  try { process.kill(pid, signal || 'SIGTERM'); return true; } catch { return false; }
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// Template role parsing
// ---------------------------------------------------------------------------

function parseTemplateRoles(filePath) {
  const yaml = parseYaml(fs.readFileSync(filePath, 'utf8'));
  const roles = yaml.roles || [];
  return roles.map(r => ({
    agent: String(r.agent || '').trim(),
    phase: typeof r.phase === 'number' ? r.phase : 1,
    auto_start: r.auto_start !== false,
    depends_on: Array.isArray(r.depends_on) ? r.depends_on.map(String) : [],
    status: 'pending',
  }));
}

// ---------------------------------------------------------------------------
// Agent validation (B14: cross-validate agent defs, B12: runtime constraints)
// ---------------------------------------------------------------------------

const AGENT_REQUIRED_FIELDS = ['name', 'scope', 'tools'];
const KNOWN_TOOLS = new Set([
  'Read', 'Edit', 'Write', 'Bash', 'Grep', 'Glob',
  'WebFetch', 'WebSearch', 'Task', 'NotebookEdit',
]);

function validateAgents(roles, root) {
  const agDir = agentsDir(root);
  const missing = [];
  const formatErrors = [];

  for (const role of roles) {
    const agentFile = path.join(agDir, `${role.agent}.yaml`);
    if (!fs.existsSync(agentFile)) {
      missing.push(role.agent);
      continue;
    }

    // B12: Validate agent definition format
    const yaml = parseYaml(fs.readFileSync(agentFile, 'utf8'));
    const errors = [];

    for (const field of AGENT_REQUIRED_FIELDS) {
      if (!(field in yaml)) {
        errors.push(`missing required field: ${field}`);
      }
    }

    if (yaml.name && typeof yaml.name !== 'string') {
      errors.push("'name' must be a string");
    }
    if (yaml.scope !== undefined && !Array.isArray(yaml.scope)) {
      errors.push("'scope' must be a list");
    }
    if (yaml.tools !== undefined) {
      if (!Array.isArray(yaml.tools)) {
        errors.push("'tools' must be a list");
      } else {
        const unknown = yaml.tools.filter(t => !KNOWN_TOOLS.has(t));
        if (unknown.length > 0) {
          errors.push(`unknown tools: ${unknown.join(', ')}`);
        }
      }
    }

    if (errors.length > 0) {
      formatErrors.push({ agent: role.agent, errors });
    }
  }

  return { missing, formatErrors };
}

// ---------------------------------------------------------------------------
// Usage
// ---------------------------------------------------------------------------

const USAGE = `Usage:
  team.js create <task-dir> [--template feature-team] [--auto]
  team.js recommend <task-dir|description>
  team.js start <team-id> [--runtime claude|codex]
  team.js status [<team-id>]
  team.js stop <team-id>
  team.js list
  team.js send <team-id> --from <agent> --to <agent|*> --type <type> "<message>"
  team.js inbox <team-id> --agent <agent> [--unread]
  team.js dashboard <team-id>
  team.js health <team-id>
  team.js restart <team-id> <agent>
  team.js report <team-id>
  team.js history
  team.js resume <team-id> [--runtime claude|codex]
  team.js watch <team-id> [--interval 30]`;

function usage() { console.log(USAGE); }

// ---------------------------------------------------------------------------
// Recommend
// ---------------------------------------------------------------------------

function cmdRecommend(args) {
  const input = args[0];
  if (!input) { console.error('error: task-dir or description required'); usage(); process.exit(1); }

  const root = oscRepoRoot();
  let description = '';

  if (fs.existsSync(path.join(root, input)) && fs.statSync(path.join(root, input)).isDirectory()) {
    const prd = path.join(root, input, 'prd.md');
    const tj = path.join(root, input, 'task.json');
    if (fs.existsSync(prd)) description = fs.readFileSync(prd, 'utf8');
    else if (fs.existsSync(tj)) description = readJson(tj).description || readJson(tj).name || '';
  } else {
    description = input;
  }
  if (!description) { console.error('error: could not extract description'); process.exit(1); }

  const descLower = description.toLowerCase();
  const tplDir = templatesDir(root);
  if (!fs.existsSync(tplDir)) { console.log('recommended: feature-team (score: 5)'); return; }

  const keywords = {
    'bugfix-team': ['bug', 'fix', '修复', '修', 'debug', '调试', '错误', 'error', 'crash', '崩溃', '问题', 'broken', '报错', '失败'],
    'feature-team': ['feature', '功能', '新增', '添加', '实现', '开发', 'add', 'create', 'build', 'implement', '支持', '接入', '集成', '重构', 'refactor', '优化', '迁移', '升级'],
  };

  let bestTemplate = '', bestScore = 0;
  const allScores = [];

  const files = fs.readdirSync(tplDir).filter(f => f.endsWith('.yaml'));
  for (const file of files) {
    const name = path.basename(file, '.yaml');
    const tplPath = path.join(tplDir, file);
    const yaml = parseYaml(fs.readFileSync(tplPath, 'utf8'));
    let score = 0;
    const kws = keywords[name] || [];
    for (const kw of kws) {
      if (descLower.includes(kw)) score += 10;
    }
    if (name === 'feature-team') score += 5;
    allScores.push({ name, score, description: yaml.description || '' });
    if (score > bestScore) { bestScore = score; bestTemplate = name; }
  }

  if (!bestTemplate) bestTemplate = 'feature-team';

  console.log(`recommended: ${bestTemplate} (score: ${bestScore})`);
  console.log('');
  console.log('all scores:');
  for (const s of allScores) {
    console.log(`  ${s.name.padEnd(20)} score=${String(s.score).padEnd(4)} ${s.description}`);
  }
  console.log('');
  console.log(`hint: use --template ${bestTemplate} with 'team.sh create'`);
  console.log("hint: future versions will support --auto for full auto-generation");
}

// ---------------------------------------------------------------------------
// Create
// ---------------------------------------------------------------------------

function cmdCreate(args) {
  const root = oscRepoRoot();
  let taskDir = '', template = 'feature-team', auto = false;
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--template' || args[i] === '-t') { template = args[++i]; }
    else if (args[i] === '--auto' || args[i] === '-a') { auto = true; }
    else positional.push(args[i]);
  }
  taskDir = positional[0] || '';
  if (!taskDir) { console.error('error: task-dir required'); usage(); process.exit(1); }

  // Normalize to relative
  if (path.isAbsolute(taskDir)) taskDir = path.relative(root, taskDir);
  if (!fs.existsSync(path.join(root, taskDir))) {
    console.error(`error: task dir not found: ${taskDir}`); process.exit(1);
  }

  // Auto-recommend template
  if (auto) {
    try {
      const genScript = path.join(oscDir(root), 'scripts', 'generate-team.sh');
      if (fs.existsSync(genScript)) {
        const outFile = path.join(templatesDir(root), 'auto-generated.yaml');
        try {
          execSync(`bash "${genScript}" "${taskDir}" --output "${outFile}"`, { cwd: root, stdio: 'pipe' });
          template = 'auto-generated';
          console.log('auto-generated team config from prd analysis');
        } catch {
          // Fallback to keyword recommendation
          const recTemplate = autoRecommend(taskDir, root);
          if (recTemplate) { template = recTemplate; console.log(`auto-selected template: ${template} (fallback from generation)`); }
        }
      } else {
        const recTemplate = autoRecommend(taskDir, root);
        if (recTemplate) { template = recTemplate; console.log(`auto-selected template: ${template}`); }
      }
    } catch { /* keep default */ }
  }

  // Read template
  const tplFile = path.join(templatesDir(root), `${template}.yaml`);
  if (!fs.existsSync(tplFile)) { console.error(`error: template not found: ${tplFile}`); process.exit(1); }

  const roles = parseTemplateRoles(tplFile);
  if (roles.length === 0) { console.error('error: no roles found in template'); process.exit(1); }

  // B14 + B12: Validate agents exist and have valid definitions
  const { missing, formatErrors } = validateAgents(roles, root);
  if (missing.length > 0) {
    for (const m of missing) {
      console.error(`error: agent '${m}' referenced in template '${template}' not found in ${agentsDir(root)}/`);
      console.error(`  hint: create ${agentsDir(root)}/${m}.yaml or remove '${m}' from the template`);
    }
    process.exit(1);
  }
  if (formatErrors.length > 0) {
    for (const { agent, errors } of formatErrors) {
      console.error(`error: agent '${agent}' has invalid definition:`);
      for (const e of errors) console.error(`  - ${e}`);
    }
    process.exit(1);
  }

  // Generate team-id
  const slug = path.basename(taskDir).replace(/^\d+-\d+-/, '');
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const teamId = `${dateStr}-${slug}`;

  // Create team directory
  const teamDir = path.join(teamsDir(root), teamId);
  mkdirp(path.join(teamDir, 'agents'));

  // Write team.json
  const teamData = {
    id: teamId,
    template,
    task: taskDir,
    status: 'created',
    created_at: nowISO(),
    roles,
  };
  writeJson(path.join(teamDir, 'team.json'), teamData);

  console.log(`created team: ${teamId}`);
  console.log(`  template: ${template}`);
  console.log(`  task: ${taskDir}`);
  console.log(`  roles: ${roles.map(r => r.agent).join(', ')}`);
}

function autoRecommend(taskDir, root) {
  // Simple keyword-based recommendation
  let description = '';
  const prd = path.join(root, taskDir, 'prd.md');
  const tj = path.join(root, taskDir, 'task.json');
  if (fs.existsSync(prd)) description = fs.readFileSync(prd, 'utf8');
  else if (fs.existsSync(tj)) { try { description = readJson(tj).description || ''; } catch {} }
  if (!description) return null;

  const lower = description.toLowerCase();
  const bugKws = ['bug', 'fix', '修复', 'debug', '错误', 'error', 'crash'];
  let bugScore = 0, featScore = 5;
  for (const kw of bugKws) { if (lower.includes(kw)) bugScore += 10; }
  const featKws = ['feature', '功能', '新增', '添加', '实现', 'add', 'create', 'implement', '重构', 'refactor'];
  for (const kw of featKws) { if (lower.includes(kw)) featScore += 10; }
  return bugScore > featScore ? 'bugfix-team' : 'feature-team';
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

function cmdStart(args) {
  const root = oscRepoRoot();
  let teamId = '', runtime = '';
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--runtime' || args[i] === '-r') { runtime = args[++i]; }
    else positional.push(args[i]);
  }
  teamId = positional[0] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }

  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  if (!runtime) runtime = detectRuntime();
  if (runtime === 'unknown') { console.error('error: cannot detect runtime (set OSC_RUNTIME or use --runtime)'); process.exit(1); }
  if (runtime !== 'claude' && runtime !== 'codex') { console.error(`error: unsupported runtime: ${runtime} (use claude|codex)`); process.exit(1); }
  console.log(`runtime: ${runtime}`);

  const teamData = readJson(teamJsonPath);
  const taskDir = teamData.task;

  // Find lowest phase with auto_start
  const minPhase = Math.min(...teamData.roles.filter(r => r.auto_start).map(r => r.phase));
  if (!isFinite(minPhase)) { console.error('error: no auto_start roles found'); process.exit(1); }

  console.log(`starting phase ${minPhase} agents...`);

  const startScript = path.join(oscDir(root), 'scripts', 'multi-agent', 'start.sh');
  const now = nowISO();

  for (const role of teamData.roles) {
    if (role.phase !== minPhase) {
      console.log(`  ${role.agent} [phase ${role.phase}] — deferred`);
      continue;
    }
    if (!role.auto_start) {
      console.log(`  ${role.agent} [phase ${role.phase}] — auto_start=false, skipped`);
      continue;
    }

    const agentJsonPath = path.join(teamDir, 'agents', `${role.agent}.json`);
    const agentData = { agent: role.agent, status: 'running', pid: null, worktree: null, started_at: now, runtime };
    writeJson(agentJsonPath, agentData);

    let pid = null, worktree = null;
    if (fs.existsSync(startScript)) {
      try {
        const output = execSync(`bash "${startScript}" "${taskDir}"`, { cwd: root, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
        const wtMatch = output.match(/worktree: (.+)/);
        const pidMatch = output.match(/pid: (\d+)/);
        if (wtMatch) worktree = wtMatch[1].trim();
        if (pidMatch) pid = parseInt(pidMatch[1], 10);
      } catch (e) {
        console.log(`  ${role.agent} [error] — start.sh failed`);
        agentData.status = 'error';
        writeJson(agentJsonPath, agentData);
        continue;
      }
    } else {
      console.error('  warn: multi-agent/start.sh not found; creating state only');
    }

    agentData.pid = pid;
    agentData.worktree = worktree;
    writeJson(agentJsonPath, agentData);
    console.log(`  ${role.agent} [started] pid=${pid || 'n/a'} worktree=${worktree || 'n/a'}`);
  }

  teamData.status = 'running';
  teamData.runtime = runtime;
  writeJson(teamJsonPath, teamData);
  console.log(`team ${teamId} is running`);
}

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

function showTeamStatus(teamDir) {
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team.json not found in ${teamDir}`); return 1; }

  const data = readJson(teamJsonPath);
  console.log(`Team: ${data.id} [${data.status}]`);
  console.log(`Template: ${data.template} | Task: ${data.task}`);
  console.log('---');

  for (const role of data.roles) {
    const agentJsonPath = path.join(teamDir, 'agents', `${role.agent}.json`);
    if (fs.existsSync(agentJsonPath)) {
      const ag = readJson(agentJsonPath);
      let agStatus = ag.status;
      if (ag.pid && agStatus === 'running' && !pidAlive(ag.pid)) {
        agStatus = 'exited';
        ag.status = 'exited';
        writeJson(agentJsonPath, ag);
      }
      console.log(`  ${role.agent.padEnd(14)} [${agStatus.padEnd(8)}]  pid=${String(ag.pid || 'n/a').padEnd(8)} worktree=${ag.worktree || 'n/a'}`);
    } else {
      const deps = (role.depends_on || []).join(', ');
      if (deps) {
        console.log(`  ${role.agent.padEnd(14)} [${role.status.padEnd(8)}]  (waiting for: ${deps})`);
      } else {
        console.log(`  ${role.agent.padEnd(14)} [${role.status.padEnd(8)}]`);
      }
    }
  }
  return 0;
}

function cmdStatus(args) {
  const root = oscRepoRoot();
  const teamId = args[0] || '';
  const base = teamsDir(root);

  if (teamId) {
    showTeamStatus(path.join(base, teamId));
  } else {
    if (!fs.existsSync(base)) { console.log('no teams found'); return; }
    const dirs = fs.readdirSync(base).filter(d => fs.existsSync(path.join(base, d, 'team.json')));
    if (dirs.length === 0) { console.log('no teams found'); return; }
    for (const d of dirs) {
      showTeamStatus(path.join(base, d));
      console.log('');
    }
  }
}

// ---------------------------------------------------------------------------
// Stop
// ---------------------------------------------------------------------------

async function cmdStop(args) {
  const teamId = args[0] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  console.log(`stopping team ${teamId}...`);

  const agentsPath = path.join(teamDir, 'agents');
  if (fs.existsSync(agentsPath)) {
    const files = fs.readdirSync(agentsPath).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const agentJsonPath = path.join(agentsPath, file);
      const ag = readJson(agentJsonPath);
      if (ag.status !== 'running') {
        console.log(`  ${ag.agent} [${ag.status}] — skip`);
        continue;
      }

      if (ag.pid && pidAlive(ag.pid)) {
        // Write shutdown signal
        fs.writeFileSync(path.join(agentsPath, `${ag.agent}.shutdown`), '');

        // Wait up to 30s for graceful shutdown
        let waited = 0;
        while (pidAlive(ag.pid) && waited < 30) {
          await sleep(1000);
          waited++;
        }

        if (pidAlive(ag.pid)) {
          killPid(ag.pid, 'SIGTERM');
          waited = 0;
          while (pidAlive(ag.pid) && waited < 10) {
            await sleep(1000);
            waited++;
          }
          if (pidAlive(ag.pid)) {
            killPid(ag.pid, 'SIGKILL');
            console.log(`  ${ag.agent} — killed (SIGKILL)`);
          } else {
            console.log(`  ${ag.agent} — stopped (SIGTERM)`);
          }
        } else {
          console.log(`  ${ag.agent} — stopped (graceful)`);
        }

        // Clean up signal/heartbeat files
        try { fs.unlinkSync(path.join(agentsPath, `${ag.agent}.shutdown`)); } catch {}
        try { fs.unlinkSync(path.join(agentsPath, `${ag.agent}.heartbeat`)); } catch {}
      } else {
        console.log(`  ${ag.agent} — not running (pid=${ag.pid || 'n/a'})`);
      }

      ag.status = 'stopped';
      writeJson(agentJsonPath, ag);
    }
  }

  // Auto-generate report on stop
  cmdReport([teamId]);

  const teamData = readJson(teamJsonPath);
  teamData.status = 'stopped';
  writeJson(teamJsonPath, teamData);
  console.log(`team ${teamId} stopped`);
}

// ---------------------------------------------------------------------------
// Resume
// ---------------------------------------------------------------------------

function cmdResume(args) {
  const root = oscRepoRoot();
  let teamId = '', runtime = '';
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--runtime' || args[i] === '-r') { runtime = args[++i]; }
    else positional.push(args[i]);
  }
  teamId = positional[0] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }

  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  const teamData = readJson(teamJsonPath);
  if (!['running', 'created', 'stopped'].includes(teamData.status)) {
    console.error(`error: team status is '${teamData.status}', cannot resume`); process.exit(1);
  }

  if (!runtime) runtime = detectRuntime();
  if (runtime === 'unknown') { console.error('error: cannot detect runtime'); process.exit(1); }
  if (runtime !== 'claude' && runtime !== 'codex') { console.error(`error: unsupported runtime: ${runtime}`); process.exit(1); }
  console.log(`runtime: ${runtime}`);
  console.log(`resuming team ${teamId}...`);

  const taskDir = teamData.task;
  const now = nowISO();
  const startScript = path.join(oscDir(root), 'scripts', 'multi-agent', 'start.sh');
  let resumed = 0;

  for (const role of teamData.roles) {
    const agentJsonPath = path.join(teamDir, 'agents', `${role.agent}.json`);

    // Skip completed agents
    if (fs.existsSync(agentJsonPath)) {
      const ag = readJson(agentJsonPath);
      if (ag.status === 'completed' || ag.status === 'done') {
        console.log(`  ${role.agent} [completed] — skip`);
        continue;
      }
    }

    // Check dependencies
    let depsMet = true;
    for (const dep of (role.depends_on || [])) {
      const depPath = path.join(teamDir, 'agents', `${dep}.json`);
      if (fs.existsSync(depPath)) {
        const depData = readJson(depPath);
        if (depData.status !== 'completed' && depData.status !== 'done') { depsMet = false; break; }
      } else { depsMet = false; break; }
    }
    if (!depsMet) { console.log(`  ${role.agent} [waiting] — dependencies not met`); continue; }

    // Restart agent
    const agentData = fs.existsSync(agentJsonPath) ? readJson(agentJsonPath) : { agent: role.agent };
    agentData.status = 'running';
    agentData.started_at = now;
    agentData.runtime = runtime;

    let pid = null, worktree = null;
    if (fs.existsSync(startScript)) {
      try {
        const output = execSync(`bash "${startScript}" "${taskDir}"`, { cwd: root, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
        const wtMatch = output.match(/worktree: (.+)/);
        const pidMatch = output.match(/pid: (\d+)/);
        if (wtMatch) worktree = wtMatch[1].trim();
        if (pidMatch) pid = parseInt(pidMatch[1], 10);
      } catch {
        console.log(`  ${role.agent} [error] — start.sh failed`);
        agentData.status = 'error';
        writeJson(agentJsonPath, agentData);
        continue;
      }
    } else {
      console.error('  warn: multi-agent/start.sh not found; updating state only');
    }

    agentData.pid = pid;
    agentData.worktree = worktree;
    writeJson(agentJsonPath, agentData);
    console.log(`  ${role.agent} [resumed] pid=${pid || 'n/a'}`);
    resumed++;
  }

  teamData.status = 'running';
  teamData.runtime = runtime;
  writeJson(teamJsonPath, teamData);
  console.log(`team ${teamId} resumed (${resumed} agents restarted)`);
}

// ---------------------------------------------------------------------------
// List
// ---------------------------------------------------------------------------

function cmdList() {
  const root = oscRepoRoot();
  const base = teamsDir(root);
  if (!fs.existsSync(base)) { console.log('no teams found'); return; }

  const dirs = fs.readdirSync(base).filter(d => fs.existsSync(path.join(base, d, 'team.json')));
  if (dirs.length === 0) { console.log('no teams found'); return; }

  console.log(`${'TEAM'.padEnd(28)} ${'TEMPLATE'.padEnd(16)} ${'TASK'.padEnd(40)} ${'STATUS'.padEnd(10)} AGENTS`);
  console.log(`${'----'.padEnd(28)} ${'--------'.padEnd(16)} ${'----'.padEnd(40)} ${'------'.padEnd(10)} ------`);

  for (const d of dirs) {
    const data = readJson(path.join(base, d, 'team.json'));
    console.log(`${data.id.padEnd(28)} ${data.template.padEnd(16)} ${data.task.padEnd(40)} ${data.status.padEnd(10)} ${data.roles.length}`);
  }
}

// ---------------------------------------------------------------------------
// Scope conflict detection
// ---------------------------------------------------------------------------

function checkScopeConflicts(teamDir) {
  const agentsPath = path.join(teamDir, 'agents');
  if (!fs.existsSync(agentsPath)) return 0;

  const agents = [];
  const files = fs.readdirSync(agentsPath).filter(f => f.endsWith('.json'));
  for (const file of files) {
    const ag = readJson(path.join(agentsPath, file));
    agents.push({
      name: ag.agent,
      scope: ag.scope || [],
      locked_files: ag.locked_files || [],
    });
  }

  let conflicts = 0;
  for (let i = 0; i < agents.length; i++) {
    for (let j = i + 1; j < agents.length; j++) {
      for (const s of agents[i].scope) {
        if (agents[j].scope.includes(s)) {
          console.error(`warning: scope conflict — ${agents[i].name} and ${agents[j].name} both claim: ${s}`);
          conflicts++;
        }
      }
      for (const f of agents[i].locked_files) {
        if (agents[j].locked_files.includes(f)) {
          console.error(`warning: locked file conflict — ${agents[i].name} and ${agents[j].name} both lock: ${f}`);
          conflicts++;
        }
      }
    }
  }
  return conflicts;
}

// ---------------------------------------------------------------------------
// Send / Inbox
// ---------------------------------------------------------------------------

function cmdSend(args) {
  let teamId = '', from = '', to = '', msgType = '', message = '';
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--from') { from = args[++i]; }
    else if (args[i] === '--to') { to = args[++i]; }
    else if (args[i] === '--type') { msgType = args[++i]; }
    else positional.push(args[i]);
  }
  teamId = positional[0] || '';
  message = positional[1] || '';

  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }
  if (!from) { console.error('error: --from required'); process.exit(1); }
  if (!to) { console.error('error: --to required'); process.exit(1); }
  if (!msgType) { console.error('error: --type required'); process.exit(1); }
  if (!message) { console.error('error: message required'); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  if (!fs.existsSync(path.join(teamDir, 'team.json'))) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  const msgDir = path.join(teamDir, 'messages');
  mkdirp(msgDir);

  const ts = nowISO();
  const filename = `${new Date().toISOString().replace(/[-:]/g, '').slice(0, 15)}-${from}.json`;
  const msgData = { from, to, type: msgType, content: message, timestamp: ts };
  writeJson(path.join(msgDir, filename), msgData);
  console.log(`sent message from=${from} to=${to} type=${msgType}`);
}

function cmdInbox(args) {
  let teamId = '', agent = '', unread = false;
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--agent') { agent = args[++i]; }
    else if (args[i] === '--unread') { unread = true; }
    else positional.push(args[i]);
  }
  teamId = positional[0] || '';

  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }
  if (!agent) { console.error('error: --agent required'); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  if (!fs.existsSync(path.join(teamDir, 'team.json'))) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  const msgDir = path.join(teamDir, 'messages');
  if (!fs.existsSync(msgDir) || fs.readdirSync(msgDir).length === 0) {
    console.log('0 message(s)'); return;
  }

  const lastReadFile = path.join(teamDir, 'agents', `${agent}.last-read`);
  let lastRead = '';
  if (unread && fs.existsSync(lastReadFile)) {
    lastRead = fs.readFileSync(lastReadFile, 'utf8').trim();
  }

  let count = 0;
  const files = fs.readdirSync(msgDir).filter(f => f.endsWith('.json')).sort();
  for (const file of files) {
    const msg = readJson(path.join(msgDir, file));
    if (msg.to !== agent && msg.to !== '*') continue;
    if (unread && lastRead && msg.timestamp <= lastRead) continue;

    console.log(`[from: ${msg.from} | type: ${msg.type} | ${msg.timestamp}]`);
    console.log(msg.content);
    console.log('');
    count++;
  }

  // Update last-read
  mkdirp(path.dirname(lastReadFile));
  fs.writeFileSync(lastReadFile, nowISO());
  console.log(`${count} message(s)`);
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function cmdDashboard(args) {
  const teamId = args[0] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  const data = readJson(teamJsonPath);

  // Section 1: Overview
  console.log(`=== Team Dashboard: ${data.id} ===`);
  console.log(`Template: ${data.template} | Task: ${data.task}`);
  console.log(`Status: ${data.status} | Created: ${data.created_at}`);
  console.log('');

  // Section 2: Agents
  console.log('--- Agents ---');
  for (const role of data.roles) {
    const agentJsonPath = path.join(teamDir, 'agents', `${role.agent}.json`);
    if (fs.existsSync(agentJsonPath)) {
      const ag = readJson(agentJsonPath);
      let agStatus = ag.status;
      if (ag.pid && agStatus === 'running' && !pidAlive(ag.pid)) agStatus = 'exited';
      console.log(`  ${role.agent.padEnd(14)} [${agStatus.padEnd(8)}]  pid=${String(ag.pid || 'n/a').padEnd(8)}`);

      // Last progress line
      if (ag.worktree) {
        const progressFile = path.join(root, ag.worktree, 'progress.log');
        if (fs.existsSync(progressFile)) {
          const lines = fs.readFileSync(progressFile, 'utf8').trim().split('\n');
          const last = lines[lines.length - 1];
          if (last) console.log(`    last: ${last}`);
        }
      }
    } else {
      const deps = (role.depends_on || []).join(', ');
      if (deps) console.log(`  ${role.agent.padEnd(14)} [pending ]  (waiting for: ${deps})`);
      else console.log(`  ${role.agent.padEnd(14)} [pending ]`);
    }
  }
  console.log('');

  // Section 3: Messages
  console.log('--- Messages ---');
  const msgDir = path.join(teamDir, 'messages');
  if (fs.existsSync(msgDir) && fs.readdirSync(msgDir).length > 0) {
    for (const role of data.roles) {
      const lastReadFile = path.join(teamDir, 'agents', `${role.agent}.last-read`);
      let lastRead = '';
      if (fs.existsSync(lastReadFile)) lastRead = fs.readFileSync(lastReadFile, 'utf8').trim();

      let unreadCount = 0;
      const msgFiles = fs.readdirSync(msgDir).filter(f => f.endsWith('.json'));
      for (const mf of msgFiles) {
        const msg = readJson(path.join(msgDir, mf));
        if (msg.to !== role.agent && msg.to !== '*') continue;
        if (lastRead && msg.timestamp <= lastRead) continue;
        unreadCount++;
      }
      console.log(`  ${role.agent}: ${unreadCount} unread`);
    }
  } else {
    console.log('  (no messages)');
  }
  console.log('');

  // Section 4: Scope conflicts
  console.log('--- Scope Conflicts ---');
  const conflicts = checkScopeConflicts(teamDir);
  if (conflicts === 0) console.log('  (none)');
}

// ---------------------------------------------------------------------------
// Lifecycle helpers
// ---------------------------------------------------------------------------

function readLifecycleConfig(agentName, root) {
  const agentYaml = path.join(agentsDir(root), `${agentName}.yaml`);
  const defaults = { restart: 'never', max_restarts: 3, timeout_minutes: 60, heartbeat_interval: 30 };
  if (!fs.existsSync(agentYaml)) return defaults;

  const yaml = parseYaml(fs.readFileSync(agentYaml, 'utf8'));
  const lc = yaml.lifecycle || {};
  return {
    restart: lc.restart || defaults.restart,
    max_restarts: typeof lc.max_restarts === 'number' ? lc.max_restarts : defaults.max_restarts,
    timeout_minutes: typeof lc.timeout_minutes === 'number' ? lc.timeout_minutes : defaults.timeout_minutes,
    heartbeat_interval: typeof lc.heartbeat_interval === 'number' ? lc.heartbeat_interval : defaults.heartbeat_interval,
  };
}

function formatUptime(seconds) {
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 60)}m`;
}

function parseEpoch(isoStr) {
  if (!isoStr) return 0;
  const d = new Date(isoStr);
  return isNaN(d.getTime()) ? 0 : Math.floor(d.getTime() / 1000);
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

function cmdHealth(args) {
  const teamId = args[0] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  const data = readJson(teamJsonPath);
  const nowEpoch = Math.floor(Date.now() / 1000);

  console.log(`Health: ${teamId}`);
  console.log('---');

  for (const role of data.roles) {
    const agentJsonPath = path.join(teamDir, 'agents', `${role.agent}.json`);
    if (!fs.existsSync(agentJsonPath)) {
      console.log(`  ${role.agent.padEnd(14)} [${'pending'.padEnd(10)}]`);
      continue;
    }

    const ag = readJson(agentJsonPath);
    const startEpoch = parseEpoch(ag.started_at);
    const uptimeSecs = startEpoch > 0 ? nowEpoch - startEpoch : 0;
    const uptimeStr = startEpoch > 0 ? formatUptime(uptimeSecs) : 'n/a';

    // Heartbeat
    const hbFile = path.join(teamDir, 'agents', `${role.agent}.heartbeat`);
    let hbStr = 'no-hb', hbAge = -1;
    if (fs.existsSync(hbFile)) {
      const hbEpoch = parseEpoch(fs.readFileSync(hbFile, 'utf8').trim());
      if (hbEpoch > 0) { hbAge = nowEpoch - hbEpoch; hbStr = `${hbAge}s ago`; }
    }

    const alive = ag.pid ? pidAlive(ag.pid) : false;
    const lc = readLifecycleConfig(role.agent, root);
    const timeoutSecs = lc.timeout_minutes * 60;

    // Determine health
    let health = 'dead';
    if (ag.status !== 'running' && ag.status !== 'error') {
      health = ag.status;
    } else if (alive) {
      if (startEpoch > 0 && uptimeSecs > timeoutSecs) {
        health = 'timed-out';
      } else if (hbAge >= 0 && hbAge < 120) {
        health = 'healthy';
      } else if (hbAge >= 120 && hbAge <= 300) {
        health = 'stale';
      } else if (hbAge < 0) {
        health = 'stale';
      } else {
        health = 'dead';
      }
    }

    console.log(`  ${role.agent.padEnd(14)} [${health.padEnd(10)}]  heartbeat=${hbStr.padEnd(10)} uptime=${uptimeStr}`);
  }
}

// ---------------------------------------------------------------------------
// Restart
// ---------------------------------------------------------------------------

function cmdRestart(args) {
  const teamId = args[0] || '';
  const agentName = args[1] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }
  if (!agentName) { console.error('error: agent name required'); usage(); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  const agentJsonPath = path.join(teamDir, 'agents', `${agentName}.json`);
  if (!fs.existsSync(agentJsonPath)) { console.error(`error: agent not found: ${agentName}`); process.exit(1); }

  const ag = readJson(agentJsonPath);

  // Stop if running
  if (ag.pid && pidAlive(ag.pid)) {
    console.log(`stopping ${agentName} (pid=${ag.pid})...`);
    killPid(ag.pid, 'SIGTERM');
    const start = Date.now();
    while (pidAlive(ag.pid) && Date.now() - start < 5000) { /* busy wait */ }
    if (pidAlive(ag.pid)) killPid(ag.pid, 'SIGKILL');
  }

  // Clean up
  try { fs.unlinkSync(path.join(teamDir, 'agents', `${agentName}.shutdown`)); } catch {}
  try { fs.unlinkSync(path.join(teamDir, 'agents', `${agentName}.heartbeat`)); } catch {}

  const restartCount = (ag.restart_count || 0) + 1;
  const teamData = readJson(teamJsonPath);
  const taskDir = teamData.task;

  const startScript = path.join(oscDir(root), 'scripts', 'multi-agent', 'start.sh');
  let newPid = null, newWorktree = null;

  if (fs.existsSync(startScript)) {
    try {
      const output = execSync(`bash "${startScript}" "${taskDir}"`, { cwd: root, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
      const wtMatch = output.match(/worktree: (.+)/);
      const pidMatch = output.match(/pid: (\d+)/);
      if (wtMatch) newWorktree = wtMatch[1].trim();
      if (pidMatch) newPid = parseInt(pidMatch[1], 10);
    } catch {
      console.error(`error: start.sh failed for ${agentName}`);
      ag.status = 'error';
      ag.restart_count = restartCount;
      writeJson(agentJsonPath, ag);
      process.exit(1);
    }
  } else {
    console.error('warn: multi-agent/start.sh not found; updating state only');
  }

  ag.status = 'running';
  ag.started_at = nowISO();
  ag.restart_count = restartCount;
  ag.pid = newPid;
  ag.worktree = newWorktree;
  writeJson(agentJsonPath, ag);
  console.log(`${agentName} restarted (restart_count=${restartCount}) pid=${newPid || 'n/a'}`);
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

function cmdReport(args) {
  const teamId = args[0] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  const data = readJson(teamJsonPath);
  const now = nowISO();
  const endEpoch = Math.floor(Date.now() / 1000);
  const startEpoch = parseEpoch(data.created_at);
  const durationSeconds = startEpoch > 0 ? endEpoch - startEpoch : 0;

  let totalAgents = 0, completedAgents = 0, errorAgents = 0;
  const agentsReport = [];

  for (const role of data.roles) {
    totalAgents++;
    const agentJsonPath = path.join(teamDir, 'agents', `${role.agent}.json`);
    let agStatus = 'pending', agStarted = '', agRuntime = '', restartCount = 0;

    if (fs.existsSync(agentJsonPath)) {
      const ag = readJson(agentJsonPath);
      agStatus = ag.status;
      agStarted = ag.started_at || '';
      agRuntime = ag.runtime || '';
      restartCount = ag.restart_count || 0;
    }

    if (agStatus === 'completed' || agStatus === 'done') completedAgents++;
    if (agStatus === 'error') errorAgents++;

    let agDuration = 0;
    if (agStarted) {
      const asEpoch = parseEpoch(agStarted);
      if (asEpoch > 0) agDuration = endEpoch - asEpoch;
    }

    agentsReport.push({ name: role.agent, status: agStatus, duration_seconds: agDuration, restarts: restartCount, runtime: agRuntime });
  }

  const successRate = totalAgents > 0 ? Math.floor(completedAgents * 100 / totalAgents) : 0;

  // Count messages
  let messageCount = 0;
  const msgDir = path.join(teamDir, 'messages');
  if (fs.existsSync(msgDir)) {
    messageCount = fs.readdirSync(msgDir).filter(f => f.endsWith('.json')).length;
  }

  const report = {
    id: data.id, template: data.template, task: data.task, status: data.status,
    created_at: data.created_at, reported_at: now, duration_seconds: durationSeconds,
    summary: { total_agents: totalAgents, completed_agents: completedAgents, error_agents: errorAgents, success_rate_percent: successRate, message_count: messageCount },
    agents: agentsReport,
  };

  writeJson(path.join(teamDir, 'report.json'), report);
  console.log(`report written to ${path.join(teamDir, 'report.json')}`);

  // Append to history
  const historyFile = path.join(oscDir(root), 'team-history.jsonl');
  fs.appendFileSync(historyFile, JSON.stringify(report) + '\n');
  console.log(`appended to ${historyFile}`);

  console.log('');
  console.log(`=== Team Report: ${data.id} ===`);
  console.log(`Template: ${data.template} | Task: ${data.task} | Status: ${data.status}`);
  console.log(`Duration: ${durationSeconds}s`);
  console.log(`Agents: ${completedAgents}/${totalAgents} completed (${successRate}%)`);
  if (errorAgents > 0) console.log(`Errors: ${errorAgents} agent(s)`);
  console.log(`Messages: ${messageCount}`);
}

// ---------------------------------------------------------------------------
// History
// ---------------------------------------------------------------------------

function cmdHistory() {
  const root = oscRepoRoot();
  const historyFile = path.join(oscDir(root), 'team-history.jsonl');
  if (!fs.existsSync(historyFile)) { console.log('no history found'); return; }

  console.log('=== Team History ===');
  console.log(`${'TEAM'.padEnd(28)} ${'TEMPLATE'.padEnd(16)} ${'STATUS'.padEnd(10)} ${'AGENTS'.padEnd(8)} ${'SUCCESS'.padEnd(10)} DURATION`);
  console.log(`${'----'.padEnd(28)} ${'--------'.padEnd(16)} ${'------'.padEnd(10)} ${'------'.padEnd(8)} ${'-------'.padEnd(10)} --------`);

  const lines = fs.readFileSync(historyFile, 'utf8').trim().split('\n');
  for (const line of lines) {
    if (!line.trim()) continue;
    const entry = JSON.parse(line);
    console.log(
      `${entry.id.padEnd(28)} ${entry.template.padEnd(16)} ${entry.status.padEnd(10)} ` +
      `${String(entry.summary.total_agents).padEnd(8)} ${(entry.summary.success_rate_percent + '%').padEnd(10)} ${entry.duration_seconds}s`
    );
  }
}

// ---------------------------------------------------------------------------
// Watch (synchronous polling — not interactive, prints and exits after one cycle
// unless run in a loop externally; for CLI use, we do a simple loop)
// ---------------------------------------------------------------------------

async function cmdWatch(args) {
  let teamId = '', interval = 30;
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--interval') { interval = parseInt(args[++i], 10) || 30; }
    else positional.push(args[i]);
  }
  teamId = positional[0] || '';
  if (!teamId) { console.error('error: team-id required'); usage(); process.exit(1); }

  const root = oscRepoRoot();
  const teamDir = path.join(teamsDir(root), teamId);
  const teamJsonPath = path.join(teamDir, 'team.json');
  if (!fs.existsSync(teamJsonPath)) { console.error(`error: team not found: ${teamId}`); process.exit(1); }

  process.on('SIGINT', () => { console.log('watch stopped'); process.exit(0); });
  process.on('SIGTERM', () => { console.log('watch stopped'); process.exit(0); });

  console.log(`watching team ${teamId} (interval=${interval}s) — Ctrl+C to stop`);

  while (true) {
    const nowEpoch = Math.floor(Date.now() / 1000);
    console.log('');
    console.log(`=== ${nowISO()} ===`);

    const data = readJson(teamJsonPath);
    for (const role of data.roles) {
      const agentJsonPath = path.join(teamDir, 'agents', `${role.agent}.json`);
      if (!fs.existsSync(agentJsonPath)) {
        console.log(`  ${role.agent.padEnd(14)} [${'pending'.padEnd(10)}]`);
        continue;
      }

      const ag = readJson(agentJsonPath);
      const startEpoch = parseEpoch(ag.started_at);
      const uptimeSecs = startEpoch > 0 ? nowEpoch - startEpoch : 0;
      const uptimeStr = startEpoch > 0 ? formatUptime(uptimeSecs) : 'n/a';

      const hbFile = path.join(teamDir, 'agents', `${role.agent}.heartbeat`);
      let hbStr = 'no-hb', hbAge = -1;
      if (fs.existsSync(hbFile)) {
        const hbEpoch = parseEpoch(fs.readFileSync(hbFile, 'utf8').trim());
        if (hbEpoch > 0) { hbAge = nowEpoch - hbEpoch; hbStr = `${hbAge}s ago`; }
      }

      const alive = ag.pid ? pidAlive(ag.pid) : false;
      const lc = readLifecycleConfig(role.agent, root);
      const timeoutSecs = lc.timeout_minutes * 60;

      let health = 'dead';
      if (ag.status !== 'running' && ag.status !== 'error') {
        health = ag.status;
      } else if (alive) {
        if (startEpoch > 0 && uptimeSecs > timeoutSecs) health = 'timed-out';
        else if (hbAge >= 0 && hbAge < 120) health = 'healthy';
        else if (hbAge >= 120 && hbAge <= 300) health = 'stale';
        else if (hbAge < 0) health = 'stale';
        else health = 'dead';
      }

      console.log(`  ${role.agent.padEnd(14)} [${health.padEnd(10)}]  heartbeat=${hbStr.padEnd(10)} uptime=${uptimeStr}`);

      // Auto-restart dead or timed-out agents
      if (health === 'dead' || health === 'timed-out') {
        const restartCount = ag.restart_count || 0;
        if (lc.restart === 'never') {
          console.log('    → not restarting (policy=never)');
        } else if (restartCount >= lc.max_restarts) {
          console.log(`    → max restarts exceeded (${restartCount}/${lc.max_restarts})`);
        } else if (lc.restart === 'always' || lc.restart === 'on-failure') {
          console.log(`    → auto-restarting (${lc.restart}, count=${restartCount})...`);
          cmdRestart([teamId, role.agent]);
        }
      }
    }

    await sleep(interval * 1000);
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);
  const cmd = args[0] || '';
  const rest = args.slice(1);

  switch (cmd) {
    case 'create':    cmdCreate(rest); break;
    case 'recommend': cmdRecommend(rest); break;
    case 'start':     cmdStart(rest); break;
    case 'status':    cmdStatus(rest); break;
    case 'stop':      await cmdStop(rest); break;
    case 'resume':    cmdResume(rest); break;
    case 'list':      cmdList(); break;
    case 'send':      cmdSend(rest); break;
    case 'inbox':     cmdInbox(rest); break;
    case 'dashboard': cmdDashboard(rest); break;
    case 'health':    cmdHealth(rest); break;
    case 'restart':   cmdRestart(rest); break;
    case 'report':    cmdReport(rest); break;
    case 'history':   cmdHistory(); break;
    case 'watch':     await cmdWatch(rest); break;
    case '': case '-h': case '--help': usage(); break;
    default: usage(); process.exit(1);
  }
}

module.exports = {
  parseYaml,
  parseTemplateRoles,
  detectRuntime,
  validateAgents,
};

if (require.main === module) {
  main().catch(e => { console.error(e.message); process.exit(1); });
}
