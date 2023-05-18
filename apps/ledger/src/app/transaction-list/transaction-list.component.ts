import { Component, OnInit } from '@angular/core';
import { LedgerService } from '../ledger.service';
import { Transaction } from '../models/transaction';
import { TransactionList } from '../types/transactionList';

@Component({
  selector: 'app-transaction-list',
  templateUrl: './transaction-list.component.html',
  styleUrls: ['./transaction-list.component.css']
})
export class TransactionListComponent {
    count = 0;
    transactions: Transaction[] = [];
    singularResourceName: string;

    constructor(
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'transaction';
    }

    ngOnInit() {
        this.ledgerService.getTransactions().subscribe(
            (transactionList: TransactionList) => {
                this.count = transactionList.count;
                this.transactions = transactionList.transactions.map((primitive) => new Transaction(primitive));
            },
            (err: any) => console.log(err),
            () => console.log('All done getting transactions')
        );
    }

    clearTransaction(event: MouseEvent, transaction: Transaction){
        event.preventDefault();
        transaction.cleared_on = new Date();
        this.ledgerService.updateTransaction(transaction.toPrimitive()).subscribe(
            () => {},
            (err: any) => console.log(err),
            () => console.log('Marked transaction as cleared')
        );
    }

}
