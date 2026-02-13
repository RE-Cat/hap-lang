#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPS (HermesProbability Science) 解释器 v0.2.2
修复: 变量替换、输出格式、特殊命令

作者: RE-Cat
GitHub: https://github.com/RE-Cat/HSP-Hermesian-probability-
"""

import re
import random
import cmd
import sys
import argparse
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class Pool:
    """概率池"""
    name: str
    total_prob: float
    items: List[str]

    @property
    def prob_per_item(self) -> float:
        return self.total_prob / len(self.items) if self.items else 0


class HPSInterpreter:
    """HPS 解释器核心"""

    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.pools: Dict[str, Pool] = {}
        self.currency: Dict[str, float] = {}
        self.inventory: List[str] = []
        self.pity_counter: int = 0
        self.total_spent: float = 0
        self.output_lines: List[str] = []

    def reset(self):
        """重置所有状态"""
        self.__init__()

    def execute(self, line: str, show_prompt: bool = False) -> List[str]:
        """执行单行代码"""
        self.output_lines = []
        line = line.strip()

        if not line:
            return []

        if show_prompt:
            print(f"hps> {line}")

        try:
            self._execute_line(line)
        except Exception as e:
            self.output_lines.append(f"[!] {str(e)}")

        return self.output_lines

    def run_script(self, code: str, verbose: bool = True) -> None:
        """批量执行脚本"""
        lines = code.strip().split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            outputs = self.execute(line, show_prompt=False)

            if verbose:
                for out in outputs:
                    print(out)

    def _execute_line(self, line: str):
        """执行单行"""
        # 注释（不包括输出）
        if line.startswith('¢') and not line.startswith('¢,'):
            comment = line[1:].strip()
            if comment:
                self.output_lines.append(f"[注] {comment}")
            return

        # 池子定义
        if line.startswith('('):
            self._define_pool(line)
            return

        # 变量赋值
        if line.startswith('#') and '=' in line and not line.startswith('#¢'):
            self._assign_variable(line)
            return

        # 目标声明
        if line.startswith('<'):
            self._execute_target(line)
            return

        # 输出（修复版）
        if line.startswith('¢,'):
            self._handle_output(line)
            return

        # 条件
        if line.startswith('?'):
            self._handle_condition(line)
            return

        # 特殊命令：/reset
        if line == '/reset':
            self.reset()
            self.output_lines.append("[✓] 已重置所有数据")
            return

        # 特殊命令：/state
        if line == '/state':
            self.output_lines.append(self.get_state())
            return

        # 循环/函数等（待实现）
        if any(line.startswith(kw) for kw in ['while', 'for', 'until', '¢.']):
            self.output_lines.append(f"[待实现] {line[:30]}...")
            return

        # 记录循环
        if line.startswith('#¢'):
            self._handle_record(line)
            return

        # 退出
        if line in ['exit', 'quit', '退出']:
            self.output_lines.append("[bye]")
            return

        self.output_lines.append(f"[?] 未知语法: {line[:40]}")

    def _define_pool(self, line: str):
        """定义池子"""
        prob_match = re.search(r'\(([\d.]+)/', line)
        if not prob_match:
            raise ValueError("池子格式: (概率/:物品)#名字")

        total_prob = float(prob_match.group(1)) / 100
        items = re.findall(r'\$(\w+)', line)

        if not items:
            raise ValueError("池子需要至少一个物品 $名字")

        name_match = re.search(r'#(\w+)', line)
        if not name_match:
            raise ValueError("池子需要命名 #名字")

        pool_name = name_match.group(1)
        self.pools[pool_name] = Pool(pool_name, total_prob, items)

        self.output_lines.append(
            f"[池] #{pool_name} | {total_prob*100}% | {len(items)}个物品"
        )

    def _assign_variable(self, line: str):
        """变量赋值"""
        match = re.match(r'#(\w+)\s*=\s*(.+)', line)
        if not match:
            raise ValueError("赋值格式: #变量 = 值")

        name, value_str = match.groups()
        value_str = value_str.strip()

        if value_str.startswith('¥'):
            self.currency[name] = float(value_str[1:])
        elif '/' in value_str:
            prob_match = re.search(r'([\d.]+)/', value_str)
            if prob_match:
                self.variables[name] = float(prob_match.group(1)) / 100
        else:
            try:
                # 尝试数学表达式
                if any(op in value_str for op in ['+', '-', '×', '÷', '*', '/']):
                    result = self._eval_math(value_str)
                    self.variables[name] = result
                else:
                    self.variables[name] = float(value_str)
            except:
                self.variables[name] = value_str

        self.output_lines.append(f"[变] #{name} = {value_str}")

    def _eval_math(self, expr: str) -> float:
        """简单数学表达式求值"""
        # 替换变量
        for var, val in self.variables.items():
            expr = expr.replace(f'#{var}', str(val))
        for var, val in self.currency.items():
            expr = expr.replace(f'#{var}', str(val))

        # 替换运算符
        expr = expr.replace('×', '*').replace('÷', '/')

        # 安全求值
        try:
            return eval(expr, {"__builtins__": {}}, {
                "random": random, "math": math,
                "π": math.pi, "e": math.e
            })
        except:
            return 0

    def _execute_target(self, line: str):
        """执行目标声明"""
        item_match = re.search(r'\$(\w+)', line)
        if not item_match:
            raise ValueError("目标格式: <$物品,#池子,*保底>")
        target_item = item_match.group(1)

        pool_match = re.search(r'#(\w+)', line)
        if not pool_match or pool_match.group(1) not in self.pools:
            raise ValueError(f"池子未定义")
        pool_name = pool_match.group(1)
        pool = self.pools[pool_name]

        pity_match = re.search(r'\*(\d+)', line)
        max_pity = int(pity_match.group(1)) if pity_match else 90

        self.output_lines.append(f"[抽] 目标: ${target_item} | 保底: {max_pity}")

        # 抽卡模拟
        for draw in range(1, max_pity + 1):
            self.pity_counter += 1
            current_prob = pool.total_prob

            if self.pity_counter > 70:
                current_prob = min(1.0, current_prob + (self.pity_counter - 70) * 0.02)

            if random.random() < current_prob:
                drawn = random.choice(pool.items)
                self.inventory.append(drawn)

                if draw <= 3 or drawn == target_item or draw >= max_pity - 2:
                    pity_tag = f" [{self.pity_counter}]" if self.pity_counter > 70 else ""
                    self.output_lines.append(f"     第{draw}抽: ${drawn}{pity_tag}")

                if drawn == target_item:
                    cost = draw * 160
                    self.total_spent += cost
                    self.output_lines.append(f"[✓] 出货! ${target_item} | {draw}抽 ¥{cost}")
                    self.pity_counter = 0
                    return
                break
        else:
            self.inventory.append(target_item)
            cost = max_pity * 160
            self.total_spent += cost
            self.output_lines.append(f"[!] 保底触发 | ${target_item} | ¥{cost}")
            self.pity_counter = 0

    def _handle_output(self, line: str):
        """处理输出（修复变量替换）"""
        content = line[2:]

        # 替换变量 #变量名
        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.variables:
                val = self.variables[var_name]
                if isinstance(val, float):
                    if val < 1:  # 概率
                        return f"{val*100}%"
                    return f"{val:.2f}"
                return str(val)
            elif var_name in self.currency:
                return f"¥{self.currency[var_name]}"
            return f"[未定义:#{var_name}]"

        content = re.sub(r'#(\w+)', replace_var, content)

        # 替换特殊变量
        content = content.replace('{inventory}', str(self.inventory))
        content = content.replace('{total_spent}', f'¥{self.total_spent}')
        content = content.replace('{pity}', str(self.pity_counter))

        # 计算简单表达式 {64800 - total_spent}
        def calc_expr(match):
            expr = match.group(1)
            try:
                # 替换 total_spent
                expr = expr.replace('total_spent', str(self.total_spent))
                expr = expr.replace('inventory.length', str(len(self.inventory)))
                # 安全计算
                result = eval(expr, {"__builtins__": {}}, {})
                return f"¥{result:.0f}" if result > 100 else str(result)
            except:
                return match.group(0)

        content = re.sub(r'\{(\d+\s*[-+]\s*[^}]+)\}', calc_expr, content)

        self.output_lines.append(f"[出] {content}")

    def _handle_condition(self, line: str):
        """条件处理（简化）"""
        self.output_lines.append(f"[条] {line}")

    def _handle_record(self, line: str):
        """记录循环（简化）"""
        times_match = re.search(r'±\s*\((\d+)\)', line)
        if times_match:
            times = int(times_match.group(1))
            # 模拟实验
            success = 0
            for _ in range(times):
                if random.random() < 0.5:
                    success += 1
            rate = success / times * 100

            self.variables['¢'] = {
                'success': success,
                'failure': times - success,
                'total': times,
                'rate': rate
            }
            self.output_lines.append(f"[录] 实验{times}次 | 成功:{success} 失败:{times-success} 率:{rate:.1f}%")
        else:
            self.output_lines.append("[录] 格式: #¢{...}±(次数)")

    def get_state(self) -> str:
        """获取当前状态"""
        lines = ["─" * 40]
        lines.append("📊 当前状态:")

        if self.pools:
            lines.append(f"  池子: {', '.join(self.pools.keys())}")
        if self.variables:
            vars_display = {}
            for k, v in self.variables.items():
                if isinstance(v, float) and v < 1:
                    vars_display[k] = f"{v*100}%"
                else:
                    vars_display[k] = v
            lines.append(f"  变量: {vars_display}")
        if self.currency:
            curr_display = {k: f"¥{v}" for k, v in self.currency.items()}
            lines.append(f"  货币: {curr_display}")

        lines.append(f"  库存: {self.inventory}")
        lines.append(f"  保底: {self.pity_counter} | 总花费: ¥{self.total_spent}")
        lines.append("─" * 40)
        return "\n".join(lines)


class HPSREPL(cmd.Cmd):
    """HPS 交互式解释器"""

    intro = """
╔══════════════════════════════════════════╗
║     HPS (HermesProbability Science)      ║
║              交互模式 v0.2.2              ║
╠══════════════════════════════════════════╣
║  输入 HPS 代码直接执行                    ║
║  特殊命令:                                ║
║    /state  - 查看当前状态                ║
║    /reset  - 重置所有数据                ║
║    /run    - 运行脚本文件                ║
║    /help   - 显示帮助                    ║
║    exit    - 退出                        ║
╚══════════════════════════════════════════╝
    """

    prompt = 'hps> '

    def __init__(self):
        super().__init__()
        self.interpreter = HPSInterpreter()

    def default(self, line: str):
        """处理默认输入"""
        if line.strip() in ['exit', 'quit']:
            print("再见! 👋")
            return True

        outputs = self.interpreter.execute(line, show_prompt=True)
        for out in outputs:
            print(out)

    def do_state(self, arg):
        """/state - 显示当前状态"""
        print(self.interpreter.get_state())

    def do_reset(self, arg):
        """/reset - 重置解释器"""
        self.interpreter.reset()
        print("[✓] 已重置所有数据")

    def do_run(self, filepath: str):
        """/run <文件> - 运行 HPS 脚本"""
        if not filepath.strip():
            print("[!] 用法: /run 文件名.hps")
            return

        try:
            with open(filepath.strip(), 'r', encoding='utf-8') as f:
                code = f.read()

            print(f"\n[运行] {filepath}")
            print("=" * 50)

            self.interpreter.run_script(code, verbose=True)

            print("=" * 50)
            print("[✓] 脚本执行完成\n")

        except FileNotFoundError:
            print(f"[!] 文件不存在: {filepath}")
        except Exception as e:
            print(f"[!] 错误: {e}")

    def do_help(self, arg):
        """/help - 显示帮助"""
        help_text = """
📘 HPS 语法速查:
═══════════════
定义池子:  (概率/:物品列表)#池子名
           例: (0.6/:$雷电,$甘雨)#UP

变量赋值:  #变量 = 值
           例: #预算 = ¥64800
           例: #计算 = 64800 ÷ 160

目标抽卡:  <$目标,#池子×:次数,*保底>
           例: <$雷电,#UP×:10,*90>

输出:      ¢,内容
           例: ¢,花费: {total_spent}
           例: ¢,结果: #变量

特殊命令:
  /state    查看当前所有状态
  /reset    清空数据重新开始
  /run 文件  运行 .hps 脚本
  exit      退出交互模式
"""
        print(help_text)

    def do_exit(self, arg):
        """exit - 退出"""
        print("再见! 👋")
        return True

    def emptyline(self):
        pass

    def cmdloop(self, intro=None):
        print(self.intro)
        while True:
            try:
                line = input(self.prompt)
                self.default(line)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                print("输入 exit 退出")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='HPS 解释器 - 让概率变得可计算',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python hps_repl.py                    # 启动交互模式
  python hps_repl.py script.hps         # 运行脚本
  python hps_repl.py script.hps -i      # 运行脚本后进入交互模式
        """
    )
    parser.add_argument('file', nargs='?', help='HPS 脚本文件 (.hps)')
    parser.add_argument('-i', '--interactive', action='store_true', 
                       help='运行脚本后进入交互模式')

    args = parser.parse_args()

    if args.file:
        interp = HPSInterpreter()

        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                code = f.read()

            print(f"[HPS] 运行脚本: {args.file}\n")
            interp.run_script(code, verbose=True)

            if args.interactive:
                print()
                repl = HPSREPL()
                repl.interpreter = interp
                repl.cmdloop()

        except FileNotFoundError:
            print(f"[!] 找不到文件: {args.file}")
            sys.exit(1)
        except Exception as e:
            print(f"[!] 错误: {e}")
            sys.exit(1)
    else:
        repl = HPSREPL()
        repl.cmdloop()


if __name__ == "__main__":
    main()
