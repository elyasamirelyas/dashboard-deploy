lines = open('agents/orchestrator.py', encoding='utf-8').readlines()
start = next(i for i, l in enumerate(lines) if l.startswith('def stage_migration'))
end = next(i for i in range(start+1, len(lines)) if lines[i].startswith('def '))
for l in lines[start:end]:
    print(repr(l))