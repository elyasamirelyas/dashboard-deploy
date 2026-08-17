# fix8.py - archived one-off patch script. Unlike most of the others in
# this folder, it uses a relative path ("orchestrator.py", meant to be run
# from inside agents/) instead of an old absolute dev path - but it's
# still inert against the current file, for a different reason: the
# anchor line it's looking for (the Lombok version check) doesn't exist
# in orchestrator.py anymore. This patch added the auto-add-jacoco-plugin
# logic right after that anchor. That logic later turned out to be dead
# code - a premature `return` earlier in the same function made it (and
# a few other fixes added around the same time) permanently unreachable,
# which was only discovered and cleaned up much later during a general
# simplification pass. So this file is a record of a fix that was written,
# silently never ran, and was eventually removed rather than reactivated.

import re

path = "orchestrator.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

anchor = '    if "org.projectlombok" in pom and "<lombok.version>" not in pom:'
if anchor not in src:
    print("ANCHOR NOT FOUND - STOPPED, NO CHANGES MADE")
    raise SystemExit(1)

if 'elif "jacoco-maven-plugin" not in pom:' in src:
    print("ALREADY PATCHED - NO CHANGES MADE")
    raise SystemExit(0)

insert = '''    elif "jacoco-maven-plugin" not in pom:
        jacoco_plugin_xml = """        <plugin>
            <groupId>org.jacoco</groupId>
            <artifactId>jacoco-maven-plugin</artifactId>
            <version>0.8.11</version>
            <executions>
                <execution>
                    <goals>
                        <goal>prepare-agent</goal>
                    </goals>
                </execution>
                <execution>
                    <id>report</id>
                    <phase>test</phase>
                    <goals>
                        <goal>report</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
"""
        if "<plugins>" in pom:
            pom = pom.replace("<plugins>", "<plugins>\\n" + jacoco_plugin_xml, 1)
            fixes_applied.append("Added missing jacoco-maven-plugin (0.8.11) to existing <plugins> block")
        elif "<build>" in pom:
            build_block = "<build>\\n    <plugins>\\n" + jacoco_plugin_xml + "    </plugins>\\n"
            pom = pom.replace("<build>", build_block, 1)
            fixes_applied.append("Added missing jacoco-maven-plugin (0.8.11) with new <plugins> block")
        else:
            pom = pom.replace(
                "</project>",
                "<build>\\n    <plugins>\\n" + jacoco_plugin_xml + "    </plugins>\\n</build>\\n</project>"
            )
            fixes_applied.append("Added missing jacoco-maven-plugin (0.8.11) with new <build> block")
'''

src = src.replace(anchor, insert + anchor, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("PATCHED OK")