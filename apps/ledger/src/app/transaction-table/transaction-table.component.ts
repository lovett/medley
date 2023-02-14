import { Component, OnInit } from '@angular/core';
import { LedgerService } from '../ledger.service';

@Component({
  selector: 'app-transaction-table',
  templateUrl: './transaction-table.component.html',
  styleUrls: ['./transaction-table.component.css']
})
export class TransactionTableComponent implements OnInit {
    constructor(
        private ledgerService: LedgerService
    ) {}

    ngOnInit() {
        console.log('hello from transaction table oninit');

        console.log(this.ledgerService.getAccounts());

    }
}
