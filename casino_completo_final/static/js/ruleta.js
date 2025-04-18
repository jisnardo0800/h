// Lógica de apuestas y animación para el juego de ruleta
let selectedChipValue = null;
let betsMap = {};    // apuestas actuales: número -> monto total
let betsTotal = 0;   // suma de todas las apuestas actuales
let currentBalance = 0;

document.addEventListener('DOMContentLoaded', function() {
    // Obtener saldo actual del elemento de saldo en la barra de navegación
    const balanceSpan = document.getElementById('balance-display');
    if (balanceSpan) {
        currentBalance = parseInt(balanceSpan.textContent) || 0;
    }

    // Manejar selección de fichas
    const chips = document.querySelectorAll('.chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            // Deseleccionar todas y seleccionar la clicada
            chips.forEach(c => c.classList.remove('selected'));
            chip.classList.add('selected');
            selectedChipValue = parseInt(chip.getAttribute('data-value'));
        });
    });

    // Colocar apuestas en el tablero al hacer clic en un número
    const cells = document.querySelectorAll('#roulette-table .cell');
    cells.forEach(cell => {
        cell.addEventListener('click', () => {
            if (selectedChipValue === null) {
                alert('Primero selecciona una ficha.');
                return;
            }
            const num = parseInt(cell.getAttribute('data-number'));
            // Verificar que haya saldo para esta apuesta
            if (betsTotal + selectedChipValue > currentBalance) {
                alert('Saldo insuficiente para realizar esa apuesta.');
                return;
            }
            // Colocar o actualizar apuesta en ese número
            if (betsMap[num]) {
                betsMap[num] += selectedChipValue;
                // Actualizar la ficha mostrada en el tablero
                const chipElem = document.getElementById('bet-' + num);
                if (chipElem) {
                    chipElem.textContent = betsMap[num];
                }
            } else {
                betsMap[num] = selectedChipValue;
                // Crear un elemento ficha en el tablero
                const betChip = document.createElement('div');
                betChip.className = 'bet-chip';
                betChip.id = 'bet-' + num;
                betChip.textContent = selectedChipValue;
                // Centrar la ficha dentro de la celda
                betChip.style.top = '50%';
                betChip.style.left = '50%';
                betChip.style.transform = 'translate(-50%, -50%)';
                cell.appendChild(betChip);
            }
            betsTotal += selectedChipValue;
        });
    });

    // Botón "Girar"
    const spinButton = document.getElementById('spin-button');
    const wheel = document.getElementById('wheel');
    const resultMsgDiv = document.getElementById('result-message');
    let currentRotation = 0;

    spinButton.addEventListener('click', () => {
        if (Object.keys(betsMap).length === 0) {
            alert('No has realizado ninguna apuesta.');
            return;
        }
        spinButton.disabled = true;
        resultMsgDiv.textContent = 'Girando...';

        // Quitar resaltado previo del número ganador, si existe
        const prevWinCell = document.querySelector('.cell.win');
        if (prevWinCell) {
            prevWinCell.classList.remove('win');
        }

        // Preparar datos de apuestas para enviar al servidor
        const betsList = [];
        for (let num in betsMap) {
            if (betsMap.hasOwnProperty(num)) {
                betsList.push({ number: parseInt(num), amount: betsMap[num] });
            }
        }

        // Llamada al servidor para obtener resultado de la ruleta
        fetch('/ruleta/spin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ bets: betsList })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                spinButton.disabled = false;
                return;
            }
            // Calcular rotación aleatoria de la rueda
            const randomDeg = Math.floor(Math.random() * 360);
            const spins = 4; // número base de vueltas completas
            const targetRotation = currentRotation + (360 * spins) + randomDeg;
            currentRotation = targetRotation % 360;
            // Definir evento al terminar la animación de la rueda
            const onSpinEnd = () => {
                wheel.removeEventListener('transitionend', onSpinEnd);
                // Resaltar número ganador en el tablero
                const winCell = document.getElementById('cell-' + data.result);
                if (winCell) {
                    winCell.classList.add('win');
                }
                // Mostrar mensaje de resultado
                let message = `Salió el ${data.result} ${data.color}. `;
                if (data.net_change > 0) {
                    message += `¡Ganaste ${data.net_change} fichas!`;
                    resultMsgDiv.className = 'win-msg';
                } else if (data.net_change < 0) {
                    message += `Perdiste ${-data.net_change} fichas.`;
                    resultMsgDiv.className = 'lose-msg';
                } else {
                    message += `No ganaste ni perdiste fichas.`;
                    resultMsgDiv.className = 'neutral-msg';
                }
                resultMsgDiv.textContent = message;
                // Actualizar saldo mostrado
                currentBalance = data.new_balance;
                if (balanceSpan) {
                    balanceSpan.textContent = data.new_balance;
                }
                // Eliminar todas las fichas apostadas del tablero
                for (let num in betsMap) {
                    if (betsMap.hasOwnProperty(num)) {
                        const chipElem = document.getElementById('bet-' + num);
                        if (chipElem) {
                            chipElem.remove();
                        }
                    }
                }
                betsMap = {};
                betsTotal = 0;
                // Reiniciar la posición de la rueda para la próxima jugada
                wheel.style.transition = 'none';
                wheel.style.transform = `rotate(${currentRotation}deg)`;
                wheel.offsetHeight;  // forzar reflujo
                wheel.style.transition = 'transform 4s ease-out';
                // Volver a habilitar el botón de Girar
                spinButton.disabled = false;
            };
            wheel.addEventListener('transitionend', onSpinEnd);
            // Iniciar la rotación de la rueda
            wheel.style.transform = `rotate(${targetRotation}deg)`;
        })
        .catch(err => {
            console.error('Error en la respuesta de la ruleta:', err);
            spinButton.disabled = false;
        });
    });
});
