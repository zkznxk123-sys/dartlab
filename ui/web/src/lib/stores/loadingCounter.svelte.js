// Global dlCall in-flight counter — LoadingBar 가 표시 트리거.
// dlCall wrapper 가 시작/끝에 begin/end 호출. counter > 0 = active.

let _instance = null;

export function getLoadingCounter() {
	if (_instance) return _instance;
	let count = $state(0);
	_instance = {
		get count() {
			return count;
		},
		get active() {
			return count > 0;
		},
		begin() {
			count++;
		},
		end() {
			if (count > 0) count--;
		},
	};
	return _instance;
}
