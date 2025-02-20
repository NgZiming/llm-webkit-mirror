import argparse
import json
import os
import uuid
from pathlib import Path

from bench.common.result import Error_Item, Result_Detail, Result_Summary
from bench.eval.ours import eval_ours_extract_html
from llm_web_kit.dataio.filebase import (FileBasedDataReader,
                                         FileBasedDataWriter)
from llm_web_kit.libs.statics import Statics

# 选项参数
parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, help='html文件路径')
parser.add_argument('--output', type=str, help='输出文件路径')
parser.add_argument('--tool', type=str, help='抽取工具', default='ours')
args = parser.parse_args()


root = Path(__file__).parent
sourcePath = os.path.join(root, 'data/all.json')
outputPath = os.path.join(root, 'output')
pipelineConfigPath = os.path.join(root, 'config/ours_config.jsonc')
pipeline_data_path = os.path.join(root, 'config/ours_data_config.jsonl')

reader = FileBasedDataReader('')
writer = FileBasedDataWriter('')


def main():
    out = {}
    task_id = str(uuid.uuid1())
    output_path = outputPath + f'/{task_id}'
    # 创建评测结果概览
    summary = Result_Summary.create(
        task_id=task_id,
        output_path=output_path,
        total=0,
        result_summary={},
        error_count=0
    )

    # 创建评测结果详情
    detail = Result_Detail.create(
        task_id=summary.task_id,  # 使用相同的task_id
        output_path=output_path,
    )

    # 创建统计对象
    statics_total = Statics()

    # 读取html文件
    with open(sourcePath, 'r') as f:
        files = json.load(f)
        # files结构是{"filename":{"url":"","filepath":""}}，获取filepath
        for fileName in files:
            summary.total += 1
            url = files[fileName]['url']
            page_layout_type = files[fileName]['layout_type']
            filepath = files[fileName]['origin_filepath']
            html = reader.read(f'{root}/data/{filepath}').decode('utf-8')

            # 评估
            if args.tool == 'magic_html':
                from bench.eval.magic_html import eval_magic_html
                output = eval_magic_html(html, fileName)
            elif args.tool == 'unstructured':
                from bench.eval.unstructured_eval import eval_unstructured
                output = eval_unstructured(html, fileName)
            elif args.tool == 'ours':
                try:
                    print(pipelineConfigPath)
                    print(pipeline_data_path)
                    print(f'{root}/data/{filepath}')
                    output, content_list, main_html, statics = eval_ours_extract_html(pipelineConfigPath, pipeline_data_path, f'{root}/data/{filepath}', page_layout_type)
                    out['content_list'] = content_list
                    out['main_html'] = main_html
                    out['statics'] = statics
                    Statics(statics).print()
                    statics_total.merge_statics(statics)
                except Exception as e:
                    summary.error_summary['count'] += 1
                    detail.result_detail['error_result'].append(Error_Item(
                        file_path=filepath,
                        error_detail=str(e)
                    ))
            else:
                raise ValueError(f'Invalid tool: {args.tool}')

            out['url'] = url
            out['content'] = output
            out['html'] = html
            writer.write(f'{outputPath}/{args.tool}/{fileName}.jsonl', json.dumps(out).encode('utf-8') + b'\n')
    summary.finish()
    detail.finish()
    statics_total.print()
    return summary, detail


if __name__ == '__main__':
    main()
