// Тестовый «медленный» логистический сервис: отвечает через 5 c,
// чтобы проверить таймаут прокси (3 c) и срабатывание Circuit Breaker по таймаутам.
function slow(r) {
    setTimeout(function () {
        r.headersOut['Content-Type'] = 'application/json';
        r.return(200, JSON.stringify({
            status: 'slow',
            endpoint: 'slow',
            message: 'This is a deliberately slow response',
            delay: '5000ms'
        }));
    }, 5000);
}

export default { slow };
