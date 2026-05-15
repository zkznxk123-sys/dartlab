"""L0 공용 파서 — provider raw 응답을 textual evidence 로 정규화하는 헬퍼.

L1 gather/providers 가 동시에 import 해도 cross 가 발생하지 않도록 L0 으로 격상한
순수 파서 모듈을 모은다. 외부 의존은 bs4·lxml·stdlib 수준만 허용한다.
"""
