import asyncio
import os
import random


def gen_random():
    return random.randint(0, 10000)


async def io(key, exec):
    out1 = []

    proc = await asyncio.subprocess.create_subprocess_exec(
        "python3", exec,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    proc.stdin.write(key.encode())

    await asyncio.sleep(2)
    out1.append((await proc.stdout.read(1024)).decode())
    out1.append((await proc.stderr.read(1024)).decode())
    code = proc.returncode
    await proc.wait()
    return out1, code


async def get_all_tests(keys, exec: str) -> list:
    tasks = []
    for key in keys:
        tasks.append(io(key, exec))

    results = await asyncio.gather(*tasks)
    return results


def do_test(p1_exec: str, p2_exec: str, n=10) -> any:
    keys = []
    for _ in range(n):
        key = ""
        for _ in range(5):
            key += str(gen_random())
            key += '\n'
        keys.append(key)
    loop = asyncio.get_event_loop()
    p1_inst = f"{os.path.abspath(p1_exec)}"
    p1_task = loop.create_task(get_all_tests(keys, p1_inst))
    p1_result = loop.run_until_complete(p1_task)

    p2_inst = f"{os.path.abspath(p2_exec)}"
    p2_task = loop.create_task(get_all_tests(keys, p2_inst))
    p2_result = loop.run_until_complete(p2_task)

    return p1_result, p2_result


p1 = "demo.py"

p1_result, p2_result = do_test(p1, p1, 2)
for r in zip(p1_result, p2_result):
    if r[0][0][0] != r[1][0][0]:
        print(f"!!!!!stdout unmatch!!!!!\n***p1***\n{r[0][0][0]}\n***p2***\n{r[1][0][0]}")
    if r[0][0][1] != r[1][0][1]:
        print(f"!!!!!stderr unmatch!!!!!\n***p1***\n{r[0][0][1]}\n***p2***\n{r[1][0][1]}")
    if r[0][1] != r[1][1]:
        print(f"!!!!!exitcode unmatch!!!!!\n***p1***\n{r[0][1]}\n***p2***\n{r[1][1]}")
print(p1_result)
print(p2_result)
