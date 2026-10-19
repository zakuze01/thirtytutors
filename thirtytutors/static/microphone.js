// Device IDs belong to a browser origin; the desktop loopback port changes.
// A permission-only probe is never connected to the audio relay.
'use strict';
const CompanionMicrophone = (() => {
  const stop = stream => stream?.getTracks().forEach(track => track.stop());
  const failure = name => Object.assign(new Error(name), {name});
  function check(isCurrent, stream) {
    if (!isCurrent()) { stop(stream); throw failure('AbortError'); }
  }
  function match(devices, id, label) {
    const inputs = devices.filter(device => device.kind === 'audioinput');
    const exact = inputs.find(device => device.deviceId === id);
    if (exact) return exact;
    const matches = label ? inputs.filter(device => device.label === label) : [];
    return matches.length === 1 ? matches[0] : null;
  }
  async function open(mediaDevices, id, label, isCurrent = () => true) {
    const audio = {channelCount:1, echoCancellation:true, noiseSuppression:true, autoGainControl:true};
    check(isCurrent);
    let stream;
    try {
      stream = await mediaDevices.getUserMedia({audio:{...audio, ...(id ? {deviceId:{exact:id}} : {})}});
    } catch (error) {
      check(isCurrent);
      // Never retry denial, a busy device, or an unrelated capture error.
      if (!id || !['OverconstrainedError','NotFoundError'].includes(error.name)) throw error;
      // Obtain labels for this origin, then immediately release the probe.
      const probe = await mediaDevices.getUserMedia({audio:true});
      stop(probe);
      check(isCurrent);
      const devices = await mediaDevices.enumerateDevices();
      check(isCurrent);
      const selected = match(devices, id, label);
      if (!selected) throw failure('SavedMicrophoneUnavailable');
      stream = await mediaDevices.getUserMedia({audio:{...audio,deviceId:{exact:selected.deviceId}}});
    }
    check(isCurrent, stream);
    return stream;
  }
  function errorMessage(error) {
    switch (error.name) {
      case 'NotAllowedError': case 'SecurityError':
        return 'Chưa có quyền micro. Chọn Allow / Cho phép trong hộp quyền; nếu đã chặn, mở quyền micro của ứng dụng rồi thử lại.';
      case 'NotReadableError':
        return 'Micro đang bận hoặc Windows không mở được thiết bị. Đóng ứng dụng đang dùng mic rồi thử lại.';
      case 'OverconstrainedError': case 'NotFoundError': case 'SavedMicrophoneUnavailable':
        return 'Micro đã lưu không còn khả dụng. Vào Cài đặt → Cho phép và liệt kê micro, chọn lại Realtek hoặc micro bạn dùng rồi lưu.';
      default:
        return 'Không mở được micro hoặc bộ thu âm. Kiểm tra thiết bị và quyền micro rồi thử lại.';
    }
  }
  return {open, match, errorMessage};
})();
if (typeof module !== 'undefined') module.exports = CompanionMicrophone;
